from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import WebhookLeadSerializer
from .models import LeadTable, SalesInfoTable, UserList, AdviserAssignmentTracker
from .views import User


from django.db import transaction

class WebhookLeadsView(APIView):
    def post(self, request):
        if "RESPONSE" in request.data:
            response_data = request.data["RESPONSE"]
            if isinstance(response_data, list):
                leads = response_data
            elif isinstance(response_data, dict):
                leads = [response_data]
            else:
                return Response({"error": "RESPONSE must be a list or object"}, status=400)
        elif isinstance(request.data, list):
            leads = request.data
        else:
            return Response({"error": "Payload must be a list or contain a RESPONSE key"}, status=400)

        # Check for record limit
        if len(leads) > 50:
            return Response({"error": "Maximum 50 records allowed"}, status=400)

        # Fetch adviser list
        adviser_ids = list(
            UserList.objects.filter(user_role__iexact="adviser", is_deactivated=False)
            .exclude(user__isnull=True)
            .values_list("user_id", flat=True)
        )
        if not adviser_ids:
            return Response({"error": "No active advisers found."}, status=400)

        adviser_users = {user.id: user for user in User.objects.filter(id__in=adviser_ids)}
        adviser_id_list = list(adviser_users.keys())
        adviser_count = len(adviser_id_list)

        inserted = 0
        skipped = []
        errors = []

        # Atomic block for thread-safe adviser rotation
        with transaction.atomic():
            tracker, _ = AdviserAssignmentTracker.objects.select_for_update().get_or_create(key="lead_assignment")
            current_index = tracker.last_index

            for item in leads:
                phone = item.get("Phone") or item.get("SENDER_MOBILE")

                # Skip if phone already has open leads
                related_leads = LeadTable.objects.filter(calling_number=phone)
                block = False
                for lead in related_leads:
                    sales = SalesInfoTable.objects.filter(lead_table=lead)
                    if sales.exists() and not sales.filter(status__iexact="closed").exists():
                        block = True
                        break
                    elif not sales.exists():
                        block = True
                        break

                if block:
                    skipped.append({"Phone": phone, "reason": "Existing lead found with no closed sale"})
                    continue

                # Assign adviser using round-robin
                adviser_id = adviser_id_list[current_index % adviser_count]
                adviser_user = adviser_users[adviser_id]
                current_index += 1

                # Serialize and save lead
                serializer = WebhookLeadSerializer(data=item, context={'user': adviser_user})
                if serializer.is_valid():
                    serializer.save()
                    inserted += 1
                else:
                    errors.append({"Phone": phone, "error": serializer.errors})

            # Save updated index
            tracker.last_index = current_index % adviser_count
            tracker.save()

        return Response({
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors
        }, status=status.HTTP_201_CREATED)




###########################################  Meta Api Test ########################

import os
import json
import requests
import logging
from datetime import datetime
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.shortcuts import render

VERIFY_TOKEN = "my_secret_token_123"

# ⚡ Replace this with your Page Access Token (long-lived)
PAGE_ACCESS_TOKEN = "EAA5ZBgUCFFrMBPohlDeJDrOBNYHpxfA3X6ka5dKMfc033e2IG7m1O4lZCpqwu7XuNZAcpab43RIYZBDO7mwJG44fTGiNKhZBuJnRP2Fwaa4j7cjzzo2mbZAgDv37dAA35PmyvvrawMK2nLf3zChgkdfZCruw8FI9g9EWttWxSW7gsumN6PiGbWDijfzrkUy1fYuKZB7h"

GRAPH_API_URL = "https://graph.facebook.com/v23.0"


LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "facebook_webhook_log.txt")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

@csrf_exempt
def webhook(request):
    print("🔔 Webhook hit")
    print("Method:", request.method)
    print("Headers:", dict(request.headers))
    print("Raw query params:", request.GET.dict())

    if request.method == "GET":
        # Verification handshake
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Verification success — returning challenge:", challenge)
            return HttpResponse(challenge)

        print("❌ Verification failed")
        return HttpResponse("Verification failed", status=403)

    elif request.method == "POST":
        print("🔔 Webhook POST triggered")
        try:
            body_unicode = request.body.decode("utf-8", errors="ignore")
            print("RAW BODY:", body_unicode or "[EMPTY BODY]")

            data = json.loads(body_unicode or "{}")
            print("Parsed JSON:", json.dumps(data, indent=2))

            # Extract leadgen_id if present
            if "entry" in data:
                for entry in data["entry"]:
                    for change in entry.get("changes", []):
                        if change.get("field") == "leadgen":
                            lead_id = change["value"].get("leadgen_id")
                            print("🎯 Leadgen ID received:", lead_id)

                            if lead_id:
                                fetch_and_log_lead_details(lead_id)

        except Exception as e:
            print("❌ Error parsing webhook:", str(e))

        return HttpResponse("EVENT_RECEIVED", status=200)

    return HttpResponse(status=404)


def fetch_and_save_lead_details(lead_id: str):
    """Fetch lead details from Facebook Graph API and log everything."""
    url = f"{GRAPH_API_URL}/{lead_id}"
    params = {
        "access_token": PAGE_ACCESS_TOKEN,
        "fields": "created_time,field_data"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        lead_data = response.json()

        # ---- Log API response ----
        logging.info(f"📥 Fetched lead data from Graph API (Lead ID: {lead_id})")
        logging.info(json.dumps(lead_data, indent=2))

        # ---- Parse field_data ----
        parsed_fields = {}
        for field in lead_data.get("field_data", []):
            name = field.get("name")
            values = field.get("values", [])
            parsed_fields[name] = values[0] if values else None

        logging.info("✅ Parsed Lead Fields:")
        logging.info(json.dumps(parsed_fields, indent=2))

        print(f"✅ Lead data logged successfully (Lead ID: {lead_id})")

        # ✅ If you want to save to DB later, uncomment this block:

        lead = LeadTable.objects.create(
            customer_name=parsed_fields.get("full_name"),
            calling_number=parsed_fields.get("phone_number"),
            state=parsed_fields.get("state"),
            district=parsed_fields.get("city"),
            pin_code=parsed_fields.get("zip_code"),
            enquiry_source="Meta",
            sub_enquiry_source="Facebook",
            lead_date=parse_datetime(lead_data.get("created_time")) or datetime.now(),
            remark="Facebook Lead",
        )
        logging.info(f"💾 Lead saved successfully (ID: {lead.id})")


    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error fetching lead from Graph API: {str(e)}")
    except Exception as e:
        logging.exception(f"❌ Error logging lead data: {str(e)}")


# ==== Privacy/Policy views ====
# def privacy_policy(request):
#     return render(request, "policies/privacy.html")
#
# def terms_of_service(request):
#     return render(request, "policies/terms.html")
#
# def data_deletion(request):
#     return render(request, "policies/data_deletion.html")









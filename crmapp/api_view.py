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
            UserList.objects.filter(user_role__iexact="adviser", is_deactivated=False, inbound_outbound__iexact="Outbound")
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

import json
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import logging
from datetime import datetime
from django.utils.dateparse import parse_datetime


VERIFY_TOKEN = "my_secret_token_123"

# ⚡ Replace this with your Page Access Token (long-lived)
PAGE_ACCESS_TOKEN = "EAA5ZBgUCFFrMBPohlDeJDrOBNYHpxfA3X6ka5dKMfc033e2IG7m1O4lZCpqwu7XuNZAcpab43RIYZBDO7mwJG44fTGiNKhZBuJnRP2Fwaa4j7cjzzo2mbZAgDv37dAA35PmyvvrawMK2nLf3zChgkdfZCruw8FI9g9EWttWxSW7gsumN6PiGbWDijfzrkUy1fYuKZB7h"

GRAPH_API_URL = "https://graph.facebook.com/v23.0"


LOG_FILE = "/var/www/html/dial_crm/logs/meta.log"


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


def fetch_and_log_lead_details(lead_id: str):
    """Fetch lead details from Facebook Graph API and save to LeadTable with equal adviser allocation."""
    url = f"{GRAPH_API_URL}/{lead_id}"
    params = {
        "access_token": PAGE_ACCESS_TOKEN,
        "fields": "created_time,campaign_id,ad_name,form_id,campaign_name,field_data"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        lead_data = response.json()

        logging.info(f"📥 Fetched lead details for Lead ID: {lead_id}")
        logging.info(json.dumps(lead_data, indent=2))

        ############ new changes to get ##########
        campaign_id = lead_data.get("campaign_id")
        ad_name = lead_data.get("ad_name")
        form_id = lead_data.get("form_id")
        campaign_name = lead_data.get("campaign_name")

        ############ end ##########

        # ---- Extract fields ----
        parsed_fields = {}
        for field in lead_data.get("field_data", []):
            name = field.get("name")
            values = field.get("values", [])
            parsed_fields[name] = values[0] if values else None

        logging.info(f"✅ Parsed Lead Fields: {json.dumps(parsed_fields, indent=2)}")

        # ==============================
        #     ADVISER ALLOCATION
        # ==============================
        adviser_ids = list(
            UserList.objects.filter(
                user_role__iexact="adviser",
                is_deactivated=False,
                inbound_outbound__iexact="Outbound"
            )
            .exclude(user__isnull=True)
            .values_list("user_id", flat=True)
        )

        if not adviser_ids:
            msg = "❌ No active advisers found."
            print(msg)
            logging.warning(msg)
            return

        adviser_users = {user.id: user for user in User.objects.filter(id__in=adviser_ids)}
        adviser_count = len(adviser_users)

        # ---- Round-robin adviser selection ----
        with transaction.atomic():
            tracker, _ = AdviserAssignmentTracker.objects.select_for_update().get_or_create(
                key="facebook_lead_assignment"
            )

            current_index = tracker.last_index or 0
            adviser_id = adviser_ids[current_index % adviser_count]
            adviser_user = adviser_users[adviser_id]

            tracker.last_index = (current_index + 1) % adviser_count
            tracker.save()

        # ==============================
        #     SAVE LEAD INTO DB
        # ==============================
        raw_number = parsed_fields.get("phone_number")

        if raw_number:
            digits_only = "".join(filter(str.isdigit, raw_number))
            cleaned_number = digits_only[-10:] if len(digits_only) >= 10 else digits_only
        else:
            cleaned_number = None

        lead = LeadTable.objects.create(
            customer_name=parsed_fields.get("full_name"),
            calling_number=cleaned_number,
            customer_type=campaign_name,
            state=parsed_fields.get("state"),
            district=parsed_fields.get("city"),
            pin_code=parsed_fields.get("zip_code"),
            enquiry_source="Meta",
            sub_enquiry_source="Facebook",
            lead_date=parse_datetime(lead_data.get("created_time")) or datetime.now(),
            remark="Facebook Lead",
            lead_upload_type="Webhook",
            created_by=adviser_user,
        )

        msg = f"💾 Lead saved successfully (ID: {lead.id}) → Adviser: {adviser_user.username}"
        print(msg)
        logging.info(msg)

    except requests.exceptions.RequestException as e:
        err = f"❌ Error fetching lead from Graph API: {str(e)}"
        print(err)
        logging.error(err)
    except Exception as e:
        err = f"❌ Error saving lead to DB: {str(e)}"
        print(err)
        logging.exception(err)



# ==== Privacy/Policy views ====
# def privacy_policy(request):
#     return render(request, "policies/privacy.html")
#
# def terms_of_service(request):
#     return render(request, "policies/terms.html")
#
# def data_deletion(request):
#     return render(request, "policies/data_deletion.html")









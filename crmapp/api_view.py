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






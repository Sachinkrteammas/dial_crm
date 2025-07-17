from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import WebhookLeadSerializer
from .models import LeadTable, SalesInfoTable, UserList
from .views import User


class WebhookLeadsView(APIView):
    def post(self, request):
        data = request.data

        if not isinstance(data, list):
            return Response({"error": "Payload must be a list"}, status=400)

        if len(data) > 50:
            return Response({"error": "Maximum 50 records allowed"}, status=400)

        inserted = 0
        skipped = []
        errors = []

        # 🔍 Fetch all active advisers
        adviser_ids = list(
            UserList.objects.filter(user_role__iexact="adviser", is_deactivated=False)
            .exclude(user__isnull=True)
            .values_list("user_id", flat=True)
        )

        if not adviser_ids:
            return Response({"error": "No active advisers found."}, status=400)

        adviser_users = {user.id: user for user in User.objects.filter(id__in=adviser_ids)}
        adviser_id_list = list(adviser_users.keys())
        adviser_index = 0

        for item in data:
            phone = item.get("Phone")

            # Skip if phone exists and no sale is closed
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
                skipped.append({
                    "Phone": phone,
                    "reason": "Existing lead found with no closed sale"
                })
                continue

            # Pick adviser user in round-robin
            adviser_id = adviser_id_list[adviser_index % len(adviser_id_list)]
            adviser_user = adviser_users[adviser_id]
            adviser_index += 1

            # Pass adviser user into serializer context
            serializer = WebhookLeadSerializer(data=item, context={'user': adviser_user})
            if serializer.is_valid():
                serializer.save()
                inserted += 1
            else:
                errors.append({"Phone": phone, "error": serializer.errors})

        return Response({
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors
        }, status=status.HTTP_201_CREATED)




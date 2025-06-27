from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import WebhookLeadSerializer
from .models import LeadTable, SalesInfoTable


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

        for item in data:
            phone = item.get("Phone")

            related_leads = LeadTable.objects.filter(calling_number=phone)

            # If phone number already exists
            if related_leads.exists():
                # Only allow insert if any related sale has status "Closed"
                if not SalesInfoTable.objects.filter(
                    lead_table__in=related_leads,
                    status__iexact="Closed"
                ).exists():
                    skipped.append({
                        "Phone": phone,
                        "reason": "Phone exists, no related sale with status 'Closed'"
                    })
                    continue  # ❌ Skip this record

            # Proceed to create lead (phone is new or previous sale was 'Closed')
            serializer = WebhookLeadSerializer(data=item)
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


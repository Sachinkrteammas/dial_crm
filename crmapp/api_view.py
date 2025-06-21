from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import WebhookLeadSerializer


class WebhookLeadsView(APIView):
    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "Payload must be a list"}, status=400)

        if len(data) > 50:
            return Response({"error": "Maximum 50 records allowed"}, status=400)

        created_count = 0
        errors = []

        for item in data:
            serializer = WebhookLeadSerializer(data=item)
            if serializer.is_valid():
                serializer.save()
                created_count += 1
            else:
                errors.append(serializer.errors)

        return Response({
            "inserted": created_count,
            "errors": errors
        }, status=status.HTTP_201_CREATED)

from rest_framework import serializers
from .models import LeadTable

class WebhookLeadSerializer(serializers.Serializer):
    Name = serializers.CharField()
    Email = serializers.EmailField()
    Phone = serializers.CharField()
    Enquiry_Type = serializers.CharField()
    Message = serializers.CharField()
    Enquiry_Source = serializers.CharField()
    Source = serializers.CharField()
    Date = serializers.DateTimeField()

    def create(self, validated_data):
        return LeadTable.objects.create(
            customer_name=validated_data["Name"],
            calling_number=validated_data["Phone"],
            enquiry_type=validated_data["Enquiry_Type"],
            remark=validated_data["Message"],
            enquiry_source=validated_data["Enquiry_Source"],
            sub_enquiry_source=validated_data["Source"],
            lead_date=validated_data["Date"],
            call_date=validated_data["Date"],
            email_id=validated_data["Email"],
            name=validated_data["Name"],
        )

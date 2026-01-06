import re
from rest_framework import serializers
from .models import LeadTable

class WebhookLeadSerializer(serializers.Serializer):
    Name = serializers.CharField()
    Email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    Phone = serializers.CharField()
    Enquiry_Type = serializers.CharField()
    Message = serializers.CharField()
    Enquiry_Source = serializers.CharField()
    Source = serializers.CharField()
    Date = serializers.DateTimeField()

    def validate_Phone(self, value):
        # Extract only digits
        digits = re.sub(r'\D', '', value)

        # Take last 10 digits (Indian mobile number)
        if len(digits) >= 10:
            digits = digits[-10:]
        else:
            raise serializers.ValidationError("Phone number must contain at least 10 digits.")

        if not re.fullmatch(r'\d{10}', digits):
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")

        return digits

    def to_internal_value(self, data):
        if "SENDER_NAME" in data:
            data = {
                "Name": data.get("SENDER_NAME"),
                "Email": data.get("SENDER_EMAIL"),
                "Phone": data.get("SENDER_MOBILE"),
                "Enquiry_Type": data.get("QUERY_TYPE"),
                "Message": data.get("QUERY_MESSAGE"),
                "Enquiry_Source": "IndiaMART",
                "Source": data.get("QUERY_MCAT_NAME", "Unknown"),
                "Date": data.get("QUERY_TIME")
            }
        return super().to_internal_value(data)

    def create(self, validated_data):
        user = self.context.get('user')
        if not user:
            raise serializers.ValidationError("No adviser user assigned.")

        return LeadTable.objects.create(
            customer_name=validated_data["Name"],
            calling_number=validated_data["Phone"],
            enquiry_type=validated_data["Enquiry_Type"],
            remark=validated_data["Message"],
            enquiry_source=validated_data["Enquiry_Source"],
            sub_enquiry_source=validated_data["Source"],
            lead_date=validated_data["Date"],
            call_date=validated_data["Date"],
            email_id=validated_data.get("Email"),
            name=validated_data["Name"],
            lead_upload_type="Webhook",
            created_by=user
        )

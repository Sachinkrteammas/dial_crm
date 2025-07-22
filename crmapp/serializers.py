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

    def to_internal_value(self, data):
        # Detect if the payload is IndiaMART format and map accordingly
        if "SENDER_NAME" in data:
            # Map IndiaMART fields to internal fields
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
            email_id=validated_data["Email"],
            name=validated_data["Name"],
            created_by=user
        )

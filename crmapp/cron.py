import requests
from django.conf import settings
from .salesdiary import save_sales_info_from_response  # your existing function
from django.utils import timezone

def fetch_lead_status_job():
    """
    This job runs every hour to fetch and update lead statuses automatically.
    """
    print("🔄 Running scheduled job: fetch_lead_status_job")

    url = f"{settings.BASE_URL}/get-lead-status"
    print(url,"url===")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            lead_data = data.get("lead_status", {})
            save_sales_info_from_response(lead_data)
            print("✅ Sales info updated successfully.")
        else:
            print("⚠️ Failed to fetch lead status:", data)
    except Exception as e:
        print("❌ Error in cron job:", str(e))

import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import LeadTable,SalesInfoTable,HistorySalesInfo
from django.contrib.auth import get_user_model
import re


AUTH_URL = "https://birlanuuat.salesdiary.in:4078/api/res_users/authenticateSystemUser"
STRUCTURE_URL = "https://birlanuuat.salesdiary.in:4078/api/sd_connects/get_business_structure"
LEAD_STATUS_URL = "https://birlanuuat.salesdiary.in:4078/api/hil_connects/getLeadStatus"
LEAD_SAVE_URL = "https://birlanuuat.salesdiary.in:4078/api/hil_connects/save_partner_lead"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpbnN0YW5jZSI6ImhpbHVhdCIsInVzZXJuYW1lIjoiYXBhcm5hIiwicGFzc3dvcmQiOiJhcGFybmEiLCJub25zZSI6IjE1NjU1ODg4ODg4ODY2In0.PtAi8fzH437NQ6pgRW8awIXd-WFDNq20ZnMzzbwx97k"


#Get Access Token Function
@csrf_exempt
def get_access_token(request):
    if request.method == 'GET':
        payload = {
            "instance": "birlanuuat",
            "method": "token",
            "token": AUTH_TOKEN
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(AUTH_URL, headers=headers, data=json.dumps(payload), timeout=15)
            response.raise_for_status()
            data = response.json()

            access_token = data.get("result", {}).get("access_token")
            print(access_token, "✅ access_token")

            if access_token:
                return JsonResponse({"status": "success", "access_token": access_token})
            else:
                return JsonResponse({"status": "error", "message": "No access_token in response", "raw": data}, status=400)

        except requests.RequestException as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Only GET method allowed"}, status=405)


#Get Business Structure Function
@csrf_exempt
def get_business_structure(request):
    if request.method == 'GET':
        # Step 1: Get access token first
        auth_payload = {
            "instance": "birlanuuat",
            "method": "token",
            "token": AUTH_TOKEN
        }
        headers = {"Content-Type": "application/json"}

        try:
            auth_response = requests.post(AUTH_URL, headers=headers, data=json.dumps(auth_payload), timeout=15)
            auth_response.raise_for_status()
            auth_data = auth_response.json()
            access_token = auth_data.get("result", {}).get("access_token")

            if not access_token:
                return JsonResponse({"status": "error", "message": "Access token not found", "raw": auth_data}, status=400)

            # Step 2: Call get_business_structure
            structure_url = f"{STRUCTURE_URL}?access_token={access_token}"
            structure_response = requests.post(structure_url, headers=headers, timeout=15)
            structure_response.raise_for_status()

            structure_data = structure_response.json()
            return JsonResponse({
                "status": "success",
                "access_token": access_token,
                "business_structure": structure_data
            })

        except requests.RequestException as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Only GET method allowed"}, status=405)

from datetime import datetime, timedelta
#Get Lead Status
@csrf_exempt
def get_lead_status(request):
    if request.method != "GET":
        return JsonResponse({"status": "error", "message": "Only GET allowed"}, status=405)

    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    # Get optional query params
    start_date = request.GET.get("start_date", str(yesterday))
    end_date = request.GET.get("end_date", str(today))
    limit = request.GET.get("limit", "150")
    offset = request.GET.get("offset", "0")

    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "PostmanRuntime/7.39.0",
        "Connection": "keep-alive",
    }

    # Step 1: Get Access Token
    auth_payload = {
        "instance": "birlanuuat",
        "method": "token",
        "token": AUTH_TOKEN,
    }

    try:
        auth_response = requests.post(AUTH_URL, headers=headers, data=json.dumps(auth_payload), verify=False, timeout=20)
        auth_response.raise_for_status()
        auth_json = auth_response.json()

        access_token = auth_json.get("result", {}).get("access_token")
        if not access_token:
            return JsonResponse({
                "status": "error",
                "message": "Access token not found in response",
                "auth_response": auth_json,
            }, status=400)

        #  Step 2: Build lead status URL (exactly like working Postman one)
        lead_status_url = (
            f"{LEAD_STATUS_URL}?access_token={access_token}"
            f"&start_date={start_date}"
            f"&end_date={end_date}"
            f"&limit={limit}"
            f"&offset={offset}"
        )
        print("🔹 LeadStatus URL:", lead_status_url)

        #  Step 3: Make POST request (empty body)
        lead_response = requests.post(lead_status_url, headers=headers, data=json.dumps({}), verify=False, timeout=20)
        lead_response.raise_for_status()

        return JsonResponse({
            "status": "success",
            "access_token": access_token,
            "lead_status": lead_response.json(),
        })

    except requests.exceptions.Timeout:
        return JsonResponse({"status": "error", "message": "Request timed out"}, status=504)

    except requests.exceptions.RequestException as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def save_lead_status(request, lead_id=None):
    if request.method == "POST" or lead_id:
        headers = {"Content-Type": "application/json"}

        try:
            # Authenticate and get access token
            auth_payload = {
                "instance": "birlanuuat",
                "method": "token",
                "token": AUTH_TOKEN,
            }
            auth_response = requests.post(
                AUTH_URL, headers=headers, data=json.dumps(auth_payload), timeout=15
            )
            auth_response.raise_for_status()

            access_token = auth_response.json().get("result", {}).get("access_token")
            if not access_token:
                return JsonResponse(
                    {"status": "error", "message": "Access token not found"},
                    status=400,
                )

            if lead_id:
                # Build payload dynamically from your database LeadTable
                lead = LeadTable.objects.get(id=lead_id)

                buyer_type_map = {
                    "Architect": "influencer",
                    "Carpenter": "influencer",
                    "Contractor": "influencer",
                    "Distributor": "supplier",
                    "Engineer": "influencer",
                    "Fabricator": "influencer",
                    "Individual Buyer": "influencer",
                    "Industrial": "project",
                    "Others": "influencer",
                    "Mason": "influencer",
                    "Painter": "influencer",
                    "Plumber": "influencer",
                    "Retailer": "retailer",
                    "Wholesaler/Stockist": "influencer",
                }
                partner_type = buyer_type_map.get(lead.buyer_type)

                payload = {
                    "data": [{
                        "name": lead.name or " ",
                        "date": lead.lead_date.strftime("%Y-%m-%d") if lead.lead_date else "",
						"partner_type": partner_type,
                        "potential": float(lead.order_value) if lead.order_value else 0,
                        "emp_email": lead.seller_email_id or "",
                        "email": lead.seller_email_id or "",
                        "emp_mobile": lead.seller_phone_no or "",
                        "mobile": lead.seller_phone_no or "",
                        "contact_name": lead.name or "",
                        "gst": "",
                        "pan": "",
                        "street": lead.address or "",
                        "street2": lead.landmark or "",
                        "city": lead.district or "",
                        "state": lead.state or "",
                        "country": "India",
                        "zip": lead.pin_code or "",
                        "source": lead.enquiry_source or "Exhibition",
                        "tid": str(lead.id),
                        "Interested Status": lead.lead_status or "",
                        "Sub Calling Status": lead.sub_calling_status or "",
                        "Select BUs": lead.select_bus or "",
                        "Product": lead.product or "",
                        "Remark": lead.remark or "",
                        "Alternative Number": lead.alternative_number or "",
                        "Landmark": lead.landmark or ""
                    }]
                }
            else:
                try:
                    payload = json.loads(request.body)
                    print(payload,"payload===")
                except json.JSONDecodeError:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid JSON payload"},
                        status=400,
                    )


            save_lead_url = f"{LEAD_SAVE_URL}?access_token={access_token}"

            print("Access Token:", access_token)
            print("POST →", save_lead_url)
            print("Payload:", json.dumps(payload, indent=2))

            lead_response = requests.post(
                save_lead_url, headers=headers, json=payload, timeout=20
            )
            lead_response.raise_for_status()

            print( lead_response.json()," lead_response json save ==")
            return JsonResponse(
                {
                    "status": "success",
                    "access_token": access_token,
                    "lead_response": lead_response.json(),
                }
            )

        except LeadTable.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"Lead with ID {lead_id} not found"},
                status=404,
            )
        except requests.RequestException as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse(
        {"status": "error", "message": "Only POST or internal lead push allowed"},
        status=405,
    )




######################################## save_sales_info_from_response ############

User = get_user_model()


def extract_param_value(params, key_name):
    """Extract the value of a param by its name inside param_json->params"""
    for p in params:
        if p.get("n", "").strip().lower() == key_name.strip().lower():
            v = p.get("v")
            if isinstance(v, list) and v:
                return v[0]
            return v
    return None


def extract_lead_id(tid):
    """Extract numeric lead ID from tid like 'CRM0098'."""
    if not tid:
        return None
    try:
        return int(''.join(filter(str.isdigit, str(tid))))
    except ValueError:
        return None


from django.utils import timezone
def save_sales_info_from_response(response_json, created_by_user=None):
    """
    Parse JSON response and either create or update SalesInfoTable entries.
    Avoids duplicate entries.
    """
    data_list = response_json.get("results", {}).get("data", []) or [response_json]  # Handle single item

    saved = []

    for item in data_list:
        lead_id = extract_lead_id(item.get("tid"))
        if not lead_id:
            print(f"⚠️ Skipping invalid TID: {item.get('tid')}")
            continue

        print(f"Processing Lead ID: {lead_id}")

        status_full = item.get("status", "")
        #status = status_full.split()[0] if status_full else ""
        status = status_full
        remarks = item.get("remarks")
        priority = item.get("priority")

        param_json = item.get("param_json", {}) or {}
        params = param_json.get("params", []) or []

        # Extract specific fields from params
        sale_mt = extract_param_value(params, "Expected Sale in MT") or 0
        sale_inr = extract_param_value(params, "Expected Sales in INR") or 0
        lead_status = status
        product = extract_param_value(params, "Product") or ""
        product_value = extract_param_value(params, "Product Value") or ""
        sales_team_remarks = extract_param_value(params, "Special Instructions By Sales Team") or remarks or ""

        # Ensure the lead exists
        lead_obj, _ = LeadTable.objects.get_or_create(
            id=lead_id, defaults={"name": item.get("name")}
        )

        # Use get_or_create for SalesInfoTable to avoid duplicates
        sales_info, created = SalesInfoTable.objects.get_or_create(
            lead_table=lead_obj,
            defaults={
                "sale_mt": sale_mt,
                "sale_inr": sale_inr,
                "sale_team_remarks": sales_team_remarks,
                "lead_status": lead_status,
                "cc_final_remarks_reformat": sales_team_remarks,
                "lead_category": priority,
                "status": status,
                "product": product,
                "product_value": product_value,
                "created_by": created_by_user,
                "updated_by": created_by_user,
            },
        )

        if not created:
            # ✅ Update existing record only if something changed
            changed = False
            fields_to_check = [
                ("sale_mt", sale_mt),
                ("sale_inr", sale_inr),
                ("sale_team_remarks", sales_team_remarks),
                ("lead_status", lead_status),
                ("cc_final_remarks_reformat", sales_team_remarks),
                ("lead_category", priority),
                ("status", status),
                ("product", product),
                ("product_value", product_value),
            ]

            for field, value in fields_to_check:
                if getattr(sales_info, field) != value:
                    setattr(sales_info, field, value)
                    changed = True

            if changed:
                if created_by_user:
                    sales_info.updated_by = created_by_user

                sales_info.updated_at = timezone.now()

                sales_info.save()
                action = "updated"
            else:
                action = "no_change"
        else:
            action = "created"

        saved.append({"lead_id": lead_id, "action": action})

    return saved


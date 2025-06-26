from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.contrib.sites import requests
from django.core import signing
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.signing import Signer
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.dateparse import parse_date

from .models import UserList, UserRole, FieldMaster, FieldMasterValue, MenuItem, DynamicFormData, LeadTable, ZoneTable, \
    SalesInfoTable, HistorySalesInfo, HistoryLead, BrandTable, CallDisposition, SalesContact, TBLFollowUp
from .views import render_menu


@login_required
def sales_user(request):
    # Render Menu
    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        parent_id = item.parent_id
        menu_tree.setdefault(parent_id, []).append(item)
    menu_html = render_menu(None, menu_tree)

    # Use email-based matching instead of user FK
    try:
        user_obj = UserList.objects.get(email_id=request.user.email, user_role='Sales')
    except UserList.DoesNotExist:
        return render(request, 'crmapp/sales.html', {
            'menu_html': menu_html,
            'leads': [],
            'zones': [],
            'error': "You are not authorized to view sales leads."
        })

    # Filter leads assigned to this sales user's email
    leads = LeadTable.objects.filter(seller_email_id=user_obj.email_id).order_by('-created_at')

    # Optional: Date filter
    query = request.GET.get('query')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Apply date filters
    if start_date:
        leads = leads.filter(lead_date__gte=parse_date(start_date))
    if end_date:
        leads = leads.filter(lead_date__lte=parse_date(end_date))

    if query:
        leads = leads.filter(
            Q(customer_name__icontains=query) |
            Q(calling_number__icontains=query) |
            Q(enquiry_type__icontains=query) |
            Q(enquiry_source__icontains=query)
        )

    # Apply pagination
    paginator = Paginator(leads, 10)  # 10 leads per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Zone list for filter dropdowns
    zones = ZoneTable.objects.values_list('zone', flat=True).distinct()

    return render(request, 'crmapp/sales.html', {
        'menu_html': menu_html,
        'leads': page_obj,
        'zones': zones,
        'paginator': paginator,
        'page_obj': page_obj,
    })


def sales_get_data(request):
    encrypted_data = request.GET.get('data')
    if not encrypted_data:
        message = "Missing encrypted data in the URL."
        return render(request, 'crmapp/sales_get_data.html', {'message': message})

    try:
        data = signing.loads(encrypted_data)
        uid = data.get('uid')
        email = data.get('email')
    except signing.BadSignature:
        message = "Invalid or tampered URL."
        return render(request, 'crmapp/sales_get_data.html', {'message': message})

    # Validate presence of uid and email
    if not uid:
        return render(request, 'crmapp/sales_get_data.html', {'message': "UID is missing in the encrypted data."})

    # if not email:
    #     return render(request, 'crmapp/sales_get_data.html', {'message': "Email is missing in the encrypted data."})

    # Query only if both uid and email are present
    lead = LeadTable.objects.filter(id=uid).first()

    if not lead:
        message = "No matching lead found for the given ID and email."
        return render(request, 'crmapp/sales_get_data.html', {'message': message})

    sales, created = SalesInfoTable.objects.get_or_create(lead_table=lead)

    return render(request, 'crmapp/sales_get_data.html', {'lead': lead, 'sales': sales})


def update_sales_info(request):
    if request.method == 'POST':
        lead_id = request.POST.get('lead_id')
        lead = get_object_or_404(LeadTable, id=lead_id)

        sales_info, created = SalesInfoTable.objects.get_or_create(lead_table=lead)


        sales_info.sale_mt = request.POST.get('sale_mt')
        sales_info.sale_inr = request.POST.get('sale_inr')
        sales_info.sale_team_remarks = request.POST.get('sale_team_remarks')
        sales_info.lead_status = request.POST.get('lead_status')
        sales_info.cc_final_remarks_reformat = request.POST.get('cc_final_remarks_reformat')
        sales_info.lead_category = request.POST.get('lead_category')
        sales_info.product = request.POST.get('product')
        sales_info.product_value = request.POST.get('product_value')
        sales_info.status = request.POST.get('status')

        if created:
            sales_info.created_by = request.user
        sales_info.updated_by = request.user

        sales_info.save()


        HistorySalesInfo.objects.create(
            lead_table=sales_info,
            sale_mt=sales_info.sale_mt,
            sale_inr=sales_info.sale_inr,
            sale_team_remarks=sales_info.sale_team_remarks,
            lead_status=sales_info.lead_status,
            cc_final_remarks_reformat=sales_info.cc_final_remarks_reformat,
            lead_category=sales_info.lead_category,
            product=sales_info.product,
            product_value=sales_info.product_value,
            status=sales_info.status,
            created_by=request.user,
            updated_by=request.user,
        )

        # ✅ Encrypt and redirect
        encrypted_data = signing.dumps({
            'uid': lead.id,
            'email': lead.seller_email_id
        })

        return redirect(f'/sales_get_data/?data={encrypted_data}')

    return redirect('dashboard')


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
@login_required
def lead_detail(request, lead_id):
    state = request.GET.get('state', '')
    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        parent_id = item.parent_id
        menu_tree.setdefault(parent_id, []).append(item)
    menu_html = render_menu(None, menu_tree)

    enquiry_sources = [
        "ChatBot", "Exhibition", "GetDistributor", "Inbound", "IndiaMart", "Mail", "Meta",
        "Plantix", "TradeIndia", "WebScraping", "WebSite", "Other"
    ]

    lead = get_object_or_404(LeadTable, id=lead_id)
    payload = {'uid': lead.id, 'email': lead.seller_email_id}
    encrypted_data = signing.dumps(payload)
    secure_url = request.build_absolute_uri(f"/sales_get_data/?data={encrypted_data}")

    # 🔹 Paginate Lead History
    lead_history_qs = HistoryLead.objects.filter(lead_table_id=lead_id).order_by('-created_at')
    page_lead = request.GET.get('page_lead')

    paginator_lead = Paginator(lead_history_qs, 5)
    try:
        lead_history = paginator_lead.page(page_lead)
    except PageNotAnInteger:
        lead_history = paginator_lead.page(1)
    except EmptyPage:
        lead_history = paginator_lead.page(paginator_lead.num_pages)

    # 🔹 Sales Info (not paginated because it's one-to-one)
    sales_info = SalesInfoTable.objects.filter(lead_table=lead).first()

    # 🔹 Paginate Sales History
    sales_history_qs = HistorySalesInfo.objects.filter(lead_table=sales_info) if sales_info else []
    page_sales = request.GET.get('page_sales')
    paginator_sales = Paginator(sales_history_qs, 10)
    try:
        sales_history = paginator_sales.page(page_sales)
    except PageNotAnInteger:
        sales_history = paginator_sales.page(1)
    except EmptyPage:
        sales_history = paginator_sales.page(paginator_sales.num_pages)

        # 🔹 Brand/Product/SubProduct Dropdown Data
    brand_data_qs = BrandTable.objects.all().values('brand', 'product_types', 'sub_product_types')
    brand_data = list(brand_data_qs)  # Convert queryset to list of dicts
    brands = sorted(set(item['brand'] for item in brand_data if item['brand']))  # Unique brands

    # Get call disposition data
    call_dispositions_qs = CallDisposition.objects.all().values('type', 'sub_type', 'sub_sub_type')
    call_dispositions = list(call_dispositions_qs)  # to use in JS

    lead = get_object_or_404(LeadTable, id=lead_id)
    state = lead.state

    sales_contacts = SalesContact.objects.filter(state__iexact=state).values(
        'city_custom', 'l1_name', 'l1_mail', 'l1_mobile'
    )

    # Convert to list if needed
    sales_contacts = list(sales_contacts)

    # Fetch follow-up history for this lead
    followup_qs = TBLFollowUp.objects.filter(lead_table=lead).all()
    page_followup = request.GET.get('page_followup')

    paginator_followup = Paginator(followup_qs, 5)  # Show 5 per page
    try:
        followup_history = paginator_followup.page(page_followup)
    except PageNotAnInteger:
        followup_history = paginator_followup.page(1)
    except EmptyPage:
        followup_history = paginator_followup.page(paginator_followup.num_pages)

    return render(request, 'crmapp/lead_detail.html', {
        'lead': lead,
        'menu_html': menu_html,
        'enquiry_sources': enquiry_sources,
        'secure_url': secure_url,
        'lead_history': lead_history,
        'sales_info': sales_info,
        'sales_history': sales_history,
        'brands': brands,  # list of brand strings
        'brand_data': brand_data,  # queryset or list of dicts
        'call_dispositions': call_dispositions,
        'sales_contacts': sales_contacts,
        'followup_history': followup_history,
    })



def get_zone_data(request):
    pincode = request.GET.get('pincode')

    if not pincode:
        return JsonResponse({'status': 'error', 'message': 'Pincode is required'}, status=400)

    try:
        zone_info = ZoneTable.objects.filter(pincode=pincode).first()

        print(f'SELECT * FROM zone_table WHERE pincode="{pincode}" LIMIT 1;')

        if zone_info:
            state = zone_info.state_ut or ''

            # Fetch sales contacts for the detected state
            sales_contacts = list(
                SalesContact.objects.filter(state__iexact=state).values(
                    'city_custom', 'l1_name', 'l1_mail', 'l1_mobile'
                )
            )

            return JsonResponse({
                'status': 'success',
                'district': zone_info.district or '',
                'state': state,
                'zone': zone_info.zone or '',
                'sales_contacts': sales_contacts,
            })

        else:
            return JsonResponse({'status': 'not_found', 'message': 'No data found for this pincode'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)




@login_required
def save_follow_up(request, lead_id):
    if request.method == 'POST':
        lead = get_object_or_404(LeadTable, id=lead_id)
        status = request.POST.get('status')
        sub_status = request.POST.get('sub_status')
        remark = request.POST.get('remark')
        follow_up_from = request.POST.get('follow_up')  # should be 'customer' or 'seller'

        TBLFollowUp.objects.create(
            lead_table=lead,
            status=status,
            sub_status=sub_status,
            remark=remark,
            follow_up=follow_up_from,
            created_by=request.user,
            updated_by=request.user,
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

import requests
def make_call_api(request):
    number = request.GET.get('number')

    if not number:
        return JsonResponse({'status': 'error', 'message': 'Number is required'})

    # Prepare API parameters
    api_url = "https://api.teammas.co.in/C2Capi/api.php"
    params = {
        "customer_number": number,
        "agent_user": "6666",
        "token": "VHJoc2xkZ2dkXjc1MzYzNVVVR2hzZ3M2",
    }

    try:
        response = requests.get(api_url, params=params)
        response_data = response.json()


        return JsonResponse({'status': 'success', 'api_response': response_data})

    except requests.exceptions.RequestException as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    except ValueError:
        # If response is not JSON
        return JsonResponse({'status': 'error', 'message': 'Invalid response from API'})

import openpyxl
@login_required
def leads_export(request):
    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        parent_id = item.parent_id
        menu_tree.setdefault(parent_id, []).append(item)
    menu_html = render_menu(None, menu_tree)

    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    if from_date_str and to_date_str:
        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)

        if not from_date or not to_date:
            return render(request, 'crmapp/leads_export.html', {
                "menu_html": menu_html,
                "error": "Invalid date format."
            })

        leads = HistoryLead.objects.filter(lead_date__range=(from_date, to_date))

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Leads"

        ws.append([
            'Customer Name', 'Customer Type', 'Calling Number', 'Enquiry Type', 'Enquiry Source', 'Sub Enquiry Source',
            'Lead Date', 'Call Date', 'Call Type', 'Calling Status', 'Interested Status',
            'Sub Calling Status', 'Sub Sub Calling Status', 'Select Business', 'Buyer Type',
            'Lead Status', 'Construction Level', 'Name', 'Alternative Number', 'Email ID',
            'Address', 'Landmark', 'Brand', 'Product', 'Sub Product',
            'State', 'District', 'Zone', 'Pincode', 'Agent Name',
            'Order Qty', 'Order Description', 'Order Value', 'Customer Type Select',
            'Registration Status', 'Remark', 'Secure URL', 'Seller Email ID', 'Seller Phone No',
            'Created By', 'Updated By', 'Created At', 'Updated At'
        ])

        for lead in leads:
            ws.append([
                lead.customer_name,
                lead.customer_type,
                lead.calling_number,
                lead.enquiry_type,
                lead.enquiry_source,
                lead.sub_enquiry_source,
                lead.lead_date.strftime('%Y-%m-%d') if lead.lead_date else '',
                lead.call_date.strftime('%Y-%m-%d') if lead.call_date else '',
                lead.call_type,
                lead.calling_status,
                lead.interested_status,
                lead.sub_calling_status,
                lead.sub_sub_calling_status,
                lead.select_bus,
                lead.buyer_type,
                lead.lead_status,
                lead.construction_level,
                lead.name,
                lead.alternative_number,
                lead.email_id,
                lead.address,
                lead.landmark,
                lead.brand,
                lead.product,
                lead.sub_product,
                lead.state,
                lead.district,
                lead.zone,
                lead.pin_code,
                lead.agent_name,
                lead.order_qty,
                lead.order_description,
                float(lead.order_value) if lead.order_value else '',
                lead.customer_type_select,
                lead.registration_status,
                lead.remark,
                lead.secure_url,
                lead.seller_email_id,
                lead.seller_phone_no,
                str(lead.created_by) if lead.created_by else '',
                str(lead.updated_by) if lead.updated_by else '',
                lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if lead.created_at else '',
                lead.updated_at.strftime('%Y-%m-%d %H:%M:%S') if lead.updated_at else ''
            ])

        file_stream = BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)

        return FileResponse(
            file_stream,
            as_attachment=True,
            filename='history_leads.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    # No export, show template
    return render(request, 'crmapp/leads_export.html', {
        "menu_html": menu_html
    })

@login_required
def sales_export(request):
    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        parent_id = item.parent_id
        menu_tree.setdefault(parent_id, []).append(item)
    menu_html = render_menu(None, menu_tree)

    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    if from_date_str and to_date_str:
        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)

        if not from_date or not to_date:
            return render(request, 'crmapp/sales_export.html', {
                "menu_html": menu_html,
                "error": "Invalid date format."
            })

        leads = HistorySalesInfo.objects.filter(
            created_at__date__range=(from_date, to_date)
        )

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sales Leads"

        # Header row
        ws.append([
            'Sale MT', 'Sale INR', 'Sale Team Remarks', 'Lead Status',
            'CC Final Remarks Reformat', 'Lead Category', 'Product',
            'Product Value', 'Status', 'Created By', 'Updated By',
            'Created At', 'Updated At'
        ])

        # Data rows
        for lead in leads:
            ws.append([
                lead.sale_mt,
                lead.sale_inr,
                lead.sale_team_remarks,
                lead.lead_status,
                lead.cc_final_remarks_reformat,
                lead.lead_category,
                lead.product,
                lead.product_value,
                lead.status,
                str(lead.created_by) if lead.created_by else '',
                str(lead.updated_by) if lead.updated_by else '',
                lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if lead.created_at else '',
                lead.updated_at.strftime('%Y-%m-%d %H:%M:%S') if lead.updated_at else ''
            ])

        file_stream = BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)

        return FileResponse(
            file_stream,
            as_attachment=True,
            filename='sales_history_leads.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    # Show template
    return render(request, 'crmapp/sales_export.html', {
        "menu_html": menu_html
    })

@login_required
def follow_up(request):
    # Build the menu
    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        menu_tree.setdefault(item.parent_id, []).append(item)
    menu_html = render_menu(None, menu_tree)

    # Get dates
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    if from_date_str and to_date_str:
        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)

        if not from_date or not to_date:
            return render(request, 'crmapp/follow_up.html', {
                "menu_html": menu_html,
                "error": "Invalid date format."
            })

        # ✅ Use created_at for date filtering
        followups = TBLFollowUp.objects.filter(created_at__date__range=(from_date, to_date))

        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Follow Ups"

        # Header
        ws.append([
            'Lead ID', 'Status', 'Sub Status', 'Remark', 'Follow Up',
            'Created By', 'Updated By', 'Created At'
        ])

        # Data rows
        for entry in followups:
            ws.append([
                entry.lead_table.id if entry.lead_table else '',
                entry.status,
                entry.sub_status,
                entry.remark,
                entry.follow_up,
                entry.created_by.username if entry.created_by else '',
                entry.updated_by.username if entry.updated_by else '',
                entry.created_at.strftime('%Y-%m-%d %H:%M:%S') if entry.created_at else '',
            ])

        # Save to in-memory file
        file_stream = BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)

        return FileResponse(
            file_stream,
            as_attachment=True,
            filename='follow_up_export.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    # Initial load without export
    return render(request, 'crmapp/follow_up.html', {
        "menu_html": menu_html
    })




@login_required
def main_leads_export(request):
    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        parent_id = item.parent_id
        menu_tree.setdefault(parent_id, []).append(item)
    menu_html = render_menu(None, menu_tree)

    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    if from_date_str and to_date_str:
        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)

        if not from_date or not to_date:
            return render(request, 'crmapp/leads_export.html', {
                "menu_html": menu_html,
                "error": "Invalid date format."
            })

        leads = LeadTable.objects.filter(lead_date__range=(from_date, to_date))

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Leads"

        ws.append([
            'Customer Name', 'Customer Type', 'Calling Number', 'Enquiry Type', 'Enquiry Source', 'Sub Enquiry Source',
            'Lead Date', 'Call Date', 'Call Type', 'Calling Status', 'Interested Status',
            'Sub Calling Status', 'Sub Sub Calling Status', 'Select Business', 'Buyer Type',
            'Lead Status', 'Construction Level', 'Name', 'Alternative Number', 'Email ID',
            'Address', 'Landmark', 'Brand', 'Product', 'Sub Product',
            'State', 'District', 'Zone', 'Pincode', 'Agent Name',
            'Order Qty', 'Order Description', 'Order Value', 'Customer Type Select',
            'Registration Status', 'Remark', 'Secure URL', 'Seller Email ID', 'Seller Phone No',
            'Created By', 'Updated By', 'Created At', 'Updated At'
        ])

        for lead in leads:
            ws.append([
                lead.customer_name,
                lead.customer_type,
                lead.calling_number,
                lead.enquiry_type,
                lead.enquiry_source,
                lead.sub_enquiry_source,
                lead.lead_date.strftime('%Y-%m-%d') if lead.lead_date else '',
                lead.call_date.strftime('%Y-%m-%d') if lead.call_date else '',
                lead.call_type,
                lead.calling_status,
                lead.interested_status,
                lead.sub_calling_status,
                lead.sub_sub_calling_status,
                lead.select_bus,
                lead.buyer_type,
                lead.lead_status,
                lead.construction_level,
                lead.name,
                lead.alternative_number,
                lead.email_id,
                lead.address,
                lead.landmark,
                lead.brand,
                lead.product,
                lead.sub_product,
                lead.state,
                lead.district,
                lead.zone,
                lead.pin_code,
                lead.agent_name,
                lead.order_qty,
                lead.order_description,
                float(lead.order_value) if lead.order_value else '',
                lead.customer_type_select,
                lead.registration_status,
                lead.remark,
                lead.secure_url,
                lead.seller_email_id,
                lead.seller_phone_no,
                str(lead.created_by) if lead.created_by else '',
                str(lead.updated_by) if lead.updated_by else '',
                lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if lead.created_at else '',
                lead.updated_at.strftime('%Y-%m-%d %H:%M:%S') if lead.updated_at else ''
            ])

        file_stream = BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)

        return FileResponse(
            file_stream,
            as_attachment=True,
            filename='leads_data.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    # No export, show template
    return render(request, 'crmapp/leads_export.html', {
        "menu_html": menu_html
    })
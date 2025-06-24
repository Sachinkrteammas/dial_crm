from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.signing import Signer
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.dateparse import parse_date

from .models import UserList, UserRole, FieldMaster, FieldMasterValue, MenuItem, DynamicFormData, LeadTable, ZoneTable, \
    SalesInfoTable, HistorySalesInfo, HistoryLead, BrandTable, CallDisposition, SalesContact
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

    if not email:
        return render(request, 'crmapp/sales_get_data.html', {'message': "Email is missing in the encrypted data."})

    # Query only if both uid and email are present
    lead = LeadTable.objects.filter(id=uid, seller_email_id=email).first()

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
    lead_history_qs = HistoryLead.objects.filter(lead_table=lead)
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
    })



def get_zone_data(request):
    pincode = request.GET.get('pincode')

    if not pincode:
        return JsonResponse({'status': 'error', 'message': 'Pincode is required'}, status=400)

    try:
        zone_info = ZoneTable.objects.filter(pincode=pincode).first()

        print(f'SELECT * FROM zone_table WHERE pincode="{pincode}" LIMIT 1;')

        if zone_info:
            return JsonResponse({
                'status': 'success',
                'district': zone_info.district or '',
                'state': zone_info.state_ut or '',
                'zone': zone_info.zone or ''
            })
        else:
            return JsonResponse({'status': 'not_found', 'message': 'No data found for this pincode'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.dateparse import parse_date

from .models import UserList, UserRole, FieldMaster, FieldMasterValue, MenuItem, DynamicFormData, LeadTable, ZoneTable, \
    SalesInfoTable
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
    uid = request.GET.get('uid')
    email = request.GET.get('email')

    # Search with all conditions
    lead = LeadTable.objects.filter(
        id=uid,
        seller_email_id=email,
    ).first()

    if not lead:
        message = "No matching lead found for the given ID and email."
        return render(request, 'crmapp/sales_get_data.html', {'message': message})
    # Get or create sales data for the lead
    sales, created = SalesInfoTable.objects.get_or_create(lead_table=lead)

    return render(request, 'crmapp/sales_get_data.html', {'lead': lead,
                                                          'sales': sales})


def update_sales_info(request):
    if request.method == 'POST':
        lead_id = request.POST.get('lead_id')
        lead = get_object_or_404(LeadTable, id=lead_id)

        # Either get existing sales info or create new
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

        return redirect('sales_get_data', uid=lead.id)
    else:
        return redirect('dashboard')  # Or a default fallback
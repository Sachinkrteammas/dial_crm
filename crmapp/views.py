import json
from audioop import reverse
from decimal import Decimal

from django.contrib.admin.templatetags.admin_list import search_form
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db.models import Q
from django.forms import model_to_dict
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import UserList, UserRole, FieldMaster, FieldMasterValue, MenuItem, DynamicFormData, LeadTable, ZoneTable, \
    HistoryLead, SalesInfoTable

User = get_user_model()

def crm_login(request):
    if request.method == 'POST':
        identifier = request.POST['username']
        password = request.POST['password']
        try:
            user_obj = User.objects.get(email=identifier)
            username = user_obj.username
        except User.DoesNotExist:
            username = identifier

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('lead_table')
        else:
            messages.error(request, 'Invalid credentials. Please try again.')
            return redirect('login')

    return render(request, 'crmapp/login.html')


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('signup')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, 'Account created successfully. Please log in.')
        return redirect('login')

    return render(request, 'crmapp/signup.html')

@login_required
def dashboard(request):
    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        parent_id = item.parent_id
        menu_tree.setdefault(parent_id, []).append(item)

    menu_html = render_menu(None, menu_tree)

    return render(request, 'crmapp/dashboard.html', {
        'menu_html': menu_html
    })



def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def user_list(request):
    if request.method == 'POST':
        # Get data from form
        full_name = request.POST.get('userFullname')
        email = request.POST.get('userEmail')
        password = request.POST.get('password')
        contact = request.POST.get('userContact')
        company = request.POST.get('companyName')
        role = request.POST.get('userRole')

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email address.")
            return redirect('user_list')

        if not all([full_name, email, password]):
            messages.error(request, "Full name, email, and password are required.")
            return redirect('user_list')

        if User.objects.filter(username=email).exists():
            messages.error(request, "User with this email already exists.")
            return redirect('user_list')

        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = full_name
        user.save()


        user_list_entry = UserList(
            full_name=full_name,
            email_id=email,
            password=password,
            contact_no=contact,
            company=company,
            user_role=role,
            created_by=request.user,
        )
        user_list_entry.save()

        messages.success(request, "User created successfully.")
        return redirect('user_list')
    users = UserList.objects.all().order_by('id')
    user_count = users.count()

    active_users = users.filter(is_deactivated=False)
    active_count = active_users.count()

    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        parent_id = item.parent_id
        menu_tree.setdefault(parent_id, []).append(item)

    menu_html = render_menu(None, menu_tree)

    return render(request, 'crmapp/user_list.html',{'count': user_count,'active_count': active_count,
                                                    'menu_html':menu_html})


def user_list_api(request):
    users = UserList.objects.all().order_by('id').values(
        'id', 'full_name','username', 'user_role', 'email_id', 'company', 'contact_no', 'is_deactivated'
    )
    return JsonResponse({'data': list(users)})



@login_required
def save_user(request):
    if request.method == 'POST':
        user_id = request.POST.get('edit_user_id')
        full_name = request.POST.get('userFullname')
        email = request.POST.get('userEmail')
        password = request.POST.get('password')
        contact = request.POST.get('userContact')
        company = request.POST.get('companyName')
        role = request.POST.get('userRole')
        action = request.POST.get('userAction')
        username = request.POST.get('username')

        # Validate
        if not full_name or not email or not username:
            messages.error(request, "Full name and username and email are required.")
            return redirect('user_list')

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email address.")
            return redirect('user_list')


        if user_id and user_id != "0":
            user_list_entry = UserList.objects.filter(id=int(user_id)).first()
            if not user_list_entry:
                messages.error(request, "User not found.")
                return redirect('user_list')

            user = user_list_entry.user

            if user:
                if email != user.username and User.objects.filter(username=email).exists():
                    messages.error(request, "User with this email already exists.")
                    return redirect('user_list')
                user.username = email
                user.email = email
                user.first_name = full_name
                if password:
                    user.set_password(password)
                user.save()
            else:
                if User.objects.filter(username=email).exists():
                    messages.error(request, "User with this email already exists.")
                    return redirect('user_list')
                user = User.objects.create_user(username=email, email=email, password=password)
                user.first_name = full_name
                user.save()
                user_list_entry.user = user

            # Update UserList
            user_list_entry.full_name = full_name
            user_list_entry.username = username
            user_list_entry.email_id = email
            user_list_entry.contact_no = contact
            user_list_entry.company = company
            user_list_entry.user_role = role
            user_list_entry.updated_by = request.user
            user_list_entry.is_deactivated = (action == "deactivate")
            user_list_entry.save()

            messages.success(request, "User updated successfully.")
            return redirect('user_list')


        else:
            if not password:
                messages.error(request, "Password is required for new users.")
                return redirect('user_list')

            if User.objects.filter(username=email).exists():
                messages.error(request, "User with this email already exists.")
                return redirect('user_list')

            user = User.objects.create_user(username=email, email=email, password=password)
            user.first_name = full_name
            user.save()

            UserList.objects.create(
                user=user,
                full_name=full_name,
                username=username,
                email_id=email,
                password=password,
                contact_no=contact,
                company=company,
                user_role=role,
                created_by=request.user,
                updated_by=request.user,
                is_deactivated=False  # default for new users
            )

            messages.success(request, "User created successfully.")
            return redirect('user_list')

    return redirect('user_list')


@login_required
@csrf_exempt
def delete_user(request, user_id):
    if request.method == 'POST':
        try:
            user_list_entry = get_object_or_404(UserList, id=user_id)

            # If you have a related User model
            try:
                user = User.objects.get(username=user_list_entry.email_id)
                user.delete()
            except User.DoesNotExist:
                pass  # ignore if user object does not exist

            user_list_entry.delete()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def user_roles(request):
    team_leader_count = UserList.objects.filter(user_role='team-leader').count()
    adviser_count = UserList.objects.filter(user_role='adviser').count()
    sales_count = UserList.objects.filter(user_role='Sales').count()
    admin_count = UserList.objects.filter(user_role='admin').count()
    user_count = UserList.objects.count()

    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        parent_id = item.parent_id
        menu_tree.setdefault(parent_id, []).append(item)

    menu_html = render_menu(None, menu_tree)

    return render(request, 'crmapp/roles.html', {
        'team_leader_count': team_leader_count,
        'adviser_count': adviser_count,
        'sales_count': sales_count,
        'admin_count': admin_count,
        'user_count': user_count,
        'menu_html': menu_html,
    })



@csrf_exempt
def add_role_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get("username")

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({"error": "User does not exist"}, status=404)

            # Create UserRole with valid User foreign key
            UserRole.objects.create(
                user=user,
                all_access=data["permissions"].get("all_access", False),
                user_read=data["permissions"]["user"].get("read", False),
                user_write=data["permissions"]["user"].get("write", False),
                user_create=data["permissions"]["user"].get("create", False),
                crm_read=data["permissions"]["crm"].get("read", False),
                crm_write=data["permissions"]["crm"].get("write", False),
                crm_create=data["permissions"]["crm"].get("create", False),
                created_by=user,  # Assuming same user creates the role
                updated_by=user,
            )

            return JsonResponse({"status": "success"}, status=201)

        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid data format"}, status=400)

    return JsonResponse({"error": "Invalid method"}, status=405)


from django.urls import reverse, NoReverseMatch  # Correct import


def render_menu(parent_id=None, menu_tree=None):
    html = '<ul class="menu-inner py-1">' if parent_id is None else '<ul class="menu-sub">'

    for item in menu_tree.get(parent_id, []):
        has_children = item.id in menu_tree
        html += '<li class="menu-item">'

        if has_children:
            html += '<a href="javascript:void(0);" class="menu-link menu-toggle">'
        else:
            try:
                if item.url_name:
                    url = reverse(item.url_name)  # This must work now
                else:
                    url = "#"
            except NoReverseMatch:
                url = "#"
            html += f'<a href="{url}" class="menu-link">'

        icon_html = f'<i class="menu-icon icon-base ti {getattr(item, "icon_class", "")}"></i>' if getattr(item,
                                                                                                           'icon_class',
                                                                                                           None) else ''
        html += icon_html + f'<div data-i18n="{item.name}">{item.name}</div></a>'

        if has_children:
            html += render_menu(parent_id=item.id, menu_tree=menu_tree)

        html += '</li>'
    html += '</ul>'
    return html


@login_required
def crm_creation(request):
    fields = FieldMaster.objects.prefetch_related('field_values').order_by('Priority')

    # Build menu HTML for sidebar
    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        parent_id = item.parent_id
        menu_tree.setdefault(parent_id, []).append(item)

    menu_html = render_menu(None, menu_tree)

    if request.method == "POST":
        form_data = {field.FieldName: request.POST.get(field.FieldName) for field in fields}
        print("Submitted Data:", form_data)
        # You can save form_data into another model or process it further

    return render(request, 'crmapp/crm_creation.html', {
        'fields': fields,
        'menu_html': menu_html,  # Pass menu HTML here
    })




from django.utils import timezone
@login_required
def crm_save(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            form_data = data.get('formData', {})
            fields = data.get('fields', [])

            client_id = 1

            for field in fields:
                field_name = field.get('name')
                field_type = field.get('fieldType')
                validation = field.get('fieldValidation')
                is_required = field.get('isRequired')
                priority = field.get('priority')

                # Save into FieldMaster
                field_master = FieldMaster.objects.create(
                    FieldName=field_name,
                    FieldType=field_type,
                    FieldValidation=validation,
                    RequiredCheck=is_required,
                    Priority=int(priority) if priority else None,
                    fieldNumber=None,
                    ClientId=client_id,
                    CreateDate=timezone.now(),
                    FieldStatus='Active'
                )

                if field_type == 'Drop Down':
                    options_key = field_name + '_options'
                    raw_values = form_data.get(options_key, "")
                    dropdown_values = [val.strip() for val in raw_values.split(',') if val.strip()]

                    for val in dropdown_values:
                        if not val.lower().startswith('select'):  # Skip placeholder
                            FieldMasterValue.objects.create(
                                FieldId=field_master,
                                FieldValueName=val,
                                ClientId=str(client_id),
                                FieldStatus='Active'
                            )
                else:
                    # Save plain input (Text Box / Text Area)
                    value = form_data.get(field_name)
                    if value:
                        FieldMasterValue.objects.create(
                            FieldId=field_master,
                            FieldValueName=value,
                            ClientId=str(client_id),
                            FieldStatus='Active'
                        )

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@require_POST
def delete_field(request, pk):
    try:
        field = FieldMaster.objects.get(pk=pk)
        field_name = field.FieldName
        field.delete()

    except FieldMaster.DoesNotExist:
        messages.error(request, 'Field not found.')
    except Exception as e:
        messages.error(request, f'Failed to delete field: {str(e)}')

    return redirect('crm_creation')



def get_field_data(request, pk):
    try:
        field = FieldMaster.objects.get(id=pk)
    except FieldMaster.DoesNotExist:
        raise Http404("Field not found")

    dropdown_values = []
    if field.FieldType == "Drop Down":
        dropdown_values = list(
            field.field_values.filter(FieldStatus="Active").values_list("FieldValueName", flat=True)
        )

    data = {
        "id": field.id,
        "FieldName": field.FieldName,
        "FieldType": field.FieldType,
        "FieldValidation": field.FieldValidation,
        "RequiredCheck": field.RequiredCheck == "Yes",
        "DropdownValues": ", ".join(dropdown_values),
    }

    return JsonResponse(data)

@csrf_exempt
def edit_field(request, pk):
    try:
        field = FieldMaster.objects.get(pk=pk)
    except FieldMaster.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Field not found'}, status=404)

    if request.method == 'GET':
        data = model_to_dict(field)

        if field.FieldType == 'Drop Down':
            dropdown_values = FieldMasterValue.objects.filter(FieldId=field).values_list('FieldValueName', flat=True)
            data['DropdownValues'] = ', '.join(dropdown_values)

        return JsonResponse(data)

    elif request.method == 'POST':
        field.FieldName = request.POST.get('FieldName')
        field.FieldType = request.POST.get('FieldType')
        field.FieldValidation = request.POST.get('FieldValidation')
        field.RequiredCheck = 'Yes' if request.POST.get('RequiredCheck') == 'Yes' else 'No'
        field.save()

        if field.FieldType == 'Drop Down':
            dropdown_values = request.POST.get('DropdownValues', '')
            values_list = [val.strip() for val in dropdown_values.split(',') if val.strip()]

            # Clear old values
            FieldMasterValue.objects.filter(FieldId=field).delete()

            # Save new values
            for val in values_list:
                FieldMasterValue.objects.create(FieldId=field, FieldValueName=val, ClientId=field.ClientId,
                                                FieldStatus='Active')

        return JsonResponse({'success': True})

    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)





@csrf_exempt
@login_required
def save_dynamic_form(request):
    if request.method == 'POST':
        try:
            form_data = json.loads(request.body)
            # Create a new entry
            DynamicFormData.objects.create(
                data=form_data,
                created_by=request.user
            )
            return JsonResponse({'success': True, 'message': 'Form saved successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def lead_table(request):
    # Fetch and build menu
    menu_items = MenuItem.objects.filter(is_active=True).order_by('order')
    menu_tree = {}
    for item in menu_items:
        parent_id = item.parent_id
        menu_tree.setdefault(parent_id, []).append(item)
    menu_html = render_menu(None, menu_tree)

    # Handle date filter
    query = request.GET.get('query')
    # leads = LeadTable.objects.all().order_by('-created_at')
    leads = LeadTable.objects.filter(created_by=request.user).order_by('-created_at')
    leads_search = LeadTable.objects.all().order_by('-created_at')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    calling_status = request.GET.get('calling_status')
    sub_calling_status = request.GET.get('sub_calling_status')


    if calling_status:
        leads = leads.filter(calling_status__iexact=calling_status)

    if sub_calling_status:
        leads = leads.filter(sub_calling_status__iexact=sub_calling_status)

    # Apply date filters
    if start_date:
        leads = leads.filter(lead_date__gte=parse_date(start_date))
    if end_date:
        leads = leads.filter(lead_date__lte=parse_date(end_date))

    if query:
        if query.upper().startswith("BN"):
            try:
                query_id = int(query[2:])  # take after "BN"
                leads = leads_search.filter(pk=query_id)
            except ValueError:
                leads = leads_search.none()  # invalid format like BNxx (non-numeric)
        else:
            leads = leads_search.filter(
                Q(customer_name__icontains=query) |
                Q(calling_number__icontains=query) |
                Q(enquiry_type__icontains=query) |
                Q(enquiry_source__icontains=query) |
                Q(sub_calling_status__icontains=query)
            )

    # Apply pagination
    paginator = Paginator(leads, 10)  # 10 leads per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    zones = ZoneTable.objects.values_list('zone', flat=True).distinct()

    return render(request, 'crmapp/lead.html', {
        'menu_html': menu_html,
        'leads': page_obj,
        'zones': zones,
        'paginator': paginator,
        'page_obj': page_obj,
    })


@csrf_exempt
def save_lead(request):
    if request.method == "POST":
        customer_name = request.POST.get('customer_name')
        customer_type = request.POST.get('customer_type')
        calling_number = request.POST.get('calling_number')
        enquiry_type = request.POST.get('enquiry_type')
        enquiry_source = request.POST.get('enquiry_source')
        lead_date = parse_date(request.POST.get('lead_date')) if request.POST.get('lead_date') else None

        # Step 1: Check for leads with same phone number
        matching_leads = LeadTable.objects.filter(calling_number=calling_number)
        print(matching_leads,"matching_leads")

        for lead in matching_leads:
            # Step 2: If any related SalesInfoTable has status != 'close', block
            sales_info_qs = SalesInfoTable.objects.filter(lead_table=lead)
            if sales_info_qs.exists():
                if not sales_info_qs.filter(status__iexact='closed').exists():
                    # Status is not closed → block registration
                    lead_url = request.build_absolute_uri(reverse('lead_detail', args=[lead.id]))
                    return JsonResponse({
                        'status': 'exists',
                        'message': 'Lead already exists and is still open.',
                        'lead_url': lead_url
                    })
            else:
                # No SalesInfoTable = treated as open → block registration
                lead_url = request.build_absolute_uri(reverse('lead_detail', args=[lead.id]))
                return JsonResponse({
                    'status': 'exists',
                    'message': 'Lead already exists without close status.',
                    'lead_url': lead_url
                })

        # Step 3: If no blocking lead found → allow new registration
        lead = LeadTable.objects.create(
            customer_name=customer_name,
            customer_type=customer_type,
            calling_number=calling_number,
            enquiry_type=enquiry_type,
            enquiry_source=enquiry_source,
            lead_date=lead_date,
            created_by=request.user if request.user.is_authenticated else None
        )

        return JsonResponse({'status': 'success', 'id': lead.id})

    return JsonResponse({'status': 'fail'}, status=400)



def get_lead_data(request, lead_id):
    try:
        lead = HistoryLead.objects.get(id=lead_id)

        # Create encrypted URL
        payload = {'uid': lead.id, 'email': lead.seller_email_id}
        encrypted_data = signing.dumps(payload)
        secure_url = request.build_absolute_uri(f"/sales_get_data/?data={encrypted_data}")

        data = {
            "id":lead.id,
            "customer_name": lead.customer_name,
            "customer_type": lead.customer_type,
            "calling_number": lead.calling_number,
            "enquiry_type": lead.enquiry_type,
            "enquiry_source": lead.enquiry_source,
            "sub_enquiry_source": lead.sub_enquiry_source,
            "lead_date": lead.lead_date.strftime("%Y-%m-%d") if lead.lead_date else "",
            # "call_date": lead.call_date.strftime("%Y-%m-%d") if lead.call_date else "",
            # "call_direction": lead.call_type,
            "calling_status": lead.calling_status,
            "interest_status": lead.interested_status,
            "sub_calling_status": lead.sub_calling_status,
            "sub_sub_calling_status": lead.sub_sub_calling_status,
            "category": lead.select_bus,
            "buyer_type": lead.buyer_type,
            "lead_status": lead.lead_status,
            "construction_level": lead.construction_level,
            "name": lead.name,
            "alternative_number": lead.alternative_number,
            "email_id": lead.email_id,
            "address": lead.address,
            "landmark": lead.landmark,
            "brand_name": lead.brand,
            "product": lead.product,
            "sub_product": lead.sub_product,
            "district": lead.district,
            "zone": lead.zone,
            "state": lead.state,
            "pin_code": lead.pin_code,
            # "agent_name": lead.agent_name,
            "order_qty": lead.order_qty,
            "order_description": lead.order_description,
            "order_value": str(lead.order_value) if lead.order_value else "",
            "customer_type_select": lead.customer_type_select,
            "registration_status": lead.registration_status,
            "remark": lead.remark,
            "seller_email": lead.seller_email_id,
            "seller_phone": lead.seller_phone_no,
            "secure_url": secure_url,
            "Date_display": lead.callback_time.strftime("%d %B %Y, %I:%M %p") if lead.callback_time else "",

        }
        return JsonResponse({"status": "success", "data": data})
    except LeadTable.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Lead not found"}, status=404)

import re

def sanitize_text(text):
    if text is None:
        return ''
    return re.sub(r'[^\w\s.,\-@()]', '', text)



from datetime import datetime
@csrf_exempt  # Keep or remove depending on your CSRF setup
def update_lead(request):
    if request.method == 'POST':
        try:
            lead_id = request.POST.get('lead_id')
            print("Lead ID ====", lead_id)
            if not lead_id:
                return JsonResponse({'status': 'error', 'message': 'Lead ID is required'})

            lead = LeadTable.objects.get(id=lead_id)

            # Helper function to parse date or return None
            def parse_date(date_str):
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
                except:
                    return None

            # --- Parse and set callback_time (new field) ---
            callback_time_str = request.POST.get('callback_time')
            if callback_time_str:
                try:
                    # Parse datetime in format 'YYYY-MM-DD HH:MM'
                    lead.callback_time = datetime.strptime(callback_time_str, '%Y-%m-%d %H:%M')
                except ValueError:
                    lead.callback_time = None
            else:
                lead.callback_time = None

            data= request.POST

            # Assign fields with fallback and type conversion
            lead.customer_name = data.get('customer_name', '')
            lead.customer_type = data.get('customer_type', '')
            lead.calling_number = data.get('calling_number', '')
            lead.enquiry_type = data.get('enquiry_type', '')
            lead.enquiry_source = data.get('enquiry_source', '')
            lead.sub_enquiry_source = data.get('sub_enquiry_source', '')
            lead.lead_date = parse_date(data.get('lead_date', None))
            lead.call_date = parse_date(data.get('call_date', None))
            lead.call_type = data.get('call_type', '')
            lead.calling_status = data.get('calling_status', '')
            lead.interested_status = data.get('interest_status', '')
            lead.sub_calling_status = data.get('sub_calling_status', '')
            lead.sub_sub_calling_status = data.get('sub_sub_calling_status', '')
            lead.select_bus = data.get('category', '')
            lead.buyer_type = data.get('buyer_type', '')
            lead.lead_status = data.get('lead_status', '')
            lead.construction_level = data.get('construction_level', '')
            lead.name = sanitize_text(data.get('name', ''))
            lead.alternative_number = data.get('alternative_number', '')
            lead.email_id = data.get('email_id', '')
            lead.address = sanitize_text(data.get('address', ''))
            lead.landmark = sanitize_text(data.get('landmark', ''))
            lead.brand = data.get('brand_name', '')
            lead.product = data.get('product', '')
            lead.sub_product = data.get('sub_product', '')
            lead.state = data.get('state', '')
            lead.district = data.get('district', '')
            lead.zone = data.get('zone', '')
            lead.pin_code = data.get('pin_code', '')
            # lead.agent_name = data.get('agent_name', '')

            order_qty = data.get('order_qty')
            lead.order_qty = int(order_qty) if order_qty not in (None, '', 'null') else None

            lead.order_description = sanitize_text(data.get('order_description', ''))

            order_value = data.get('order_value')
            try:
                lead.order_value = Decimal(order_value) if order_value not in (None, '', 'null') else None
            except:
                lead.order_value = None

            lead.customer_type_select = data.get('customer_type_select', '')

            lead.registration_status = data.get('registration_status', '')
            lead.remark = sanitize_text(data.get('remark', ''))
            lead.seller_email_id = data.get('seller_email', '')
            lead.seller_phone_no = data.get('seller_phone', '')

            lead.seller_email_id_L2 = data.get('seller_email_L2', '')
            lead.seller_phone_no_L2 = data.get('seller_phone_L2', '')

            lead.lead_closer_status = data.get('lead_closer_status', '')
            lead.lead_closer_status_new = data.get('lead_closer_status_new', '')

            if (lead.lead_closer_status or lead.lead_closer_status_new.lower().startswith("closed")):
                lead.lead_close_date = timezone.now().date()

            lead.final_lead_close_date = parse_date(data.get('final_lead_close_date', None))

            lead.secure_url = data.get('secure_link', '')

            lead.save()

            # --- Create HistoryLead record ---
            HistoryLead.objects.create(
                lead_table=lead,
                customer_name=lead.customer_name,
                customer_type=lead.customer_type,
                calling_number=lead.calling_number,
                enquiry_type=lead.enquiry_type,
                enquiry_source=lead.enquiry_source,
                sub_enquiry_source=lead.sub_enquiry_source,
                lead_date=lead.lead_date,
                call_date=lead.call_date,
                call_type=lead.call_type,
                calling_status=lead.calling_status,
                interested_status=lead.interested_status,
                sub_calling_status=lead.sub_calling_status,
                sub_sub_calling_status=lead.sub_sub_calling_status,
                select_bus=lead.select_bus,
                buyer_type=lead.buyer_type,
                lead_status=lead.lead_status,
                construction_level=lead.construction_level,
                name=lead.name,
                alternative_number=lead.alternative_number,
                email_id=lead.email_id,
                address=lead.address,
                landmark=lead.landmark,
                brand=lead.brand,
                product=lead.product,
                sub_product=lead.sub_product,
                state=lead.state,
                district=lead.district,
                zone=lead.zone,
                pin_code=lead.pin_code,
                agent_name=lead.agent_name,
                order_qty=lead.order_qty,
                order_description=lead.order_description,
                order_value=lead.order_value,
                customer_type_select=lead.customer_type_select,
                registration_status=lead.registration_status,
                remark=lead.remark,
                secure_url=lead.secure_url,
                seller_email_id=lead.seller_email_id,
                seller_phone_no=lead.seller_phone_no,

                seller_email_id_L2=lead.seller_email_id_L2,
                seller_phone_no_L2=lead.seller_phone_no_L2,
                callback_time=lead.callback_time,
                lead_closer_status =lead.lead_closer_status,
                lead_closer_status_new =lead.lead_closer_status_new,
                lead_close_date=lead.lead_close_date,
                final_lead_close_date=lead.final_lead_close_date,

                created_by=lead.created_by,  # or request.user if preferred
                updated_by=lead.updated_by,
            )

            # Call the email function
            # from .sales_views import send_lead_email
            # send_lead_email(request, lead_id)


            # return JsonResponse({'status': 'success'})
            messages.success(request, 'Lead updated successfully!')
            return redirect('lead_detail', lead_id=lead.id)


        except LeadTable.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Lead not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def delete_lead(request, lead_id):
    if request.method == "POST":
        try:
            lead = LeadTable.objects.get(id=lead_id)
            lead.delete()
            return JsonResponse({'status': 'success'})
        except LeadTable.DoesNotExist:
            return JsonResponse({'status': 'not_found'}, status=404)
    return JsonResponse({'status': 'invalid'}, status=400)


def get_user_emails(request):
    users = UserList.objects.filter(user_role='sales').values('id', 'email_id')
    return JsonResponse(list(users), safe=False)

def get_contact_by_email(request):
    email = request.GET.get('email')
    try:
        user = UserList.objects.get(email_id=email)
        return JsonResponse({'contact_no': user.contact_no})
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)


def get_states_by_zone(request):
    zone = request.GET.get('zone')
    states = ZoneTable.objects.filter(zone=zone).values_list('state_ut', flat=True).distinct()
    return JsonResponse({'states': list(states)})




from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt

from .models import UserList

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
            return redirect('dashboard')
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
    return render(request, 'crmapp/dashboard.html')


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

    return render(request, 'crmapp/user_list.html',{'count': user_count,'active_count': active_count})


def user_list_api(request):
    users = UserList.objects.all().order_by('id').values(
        'id', 'full_name', 'user_role', 'email_id', 'company', 'contact_no', 'is_deactivated'
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

        # Validate
        if not full_name or not email:
            messages.error(request, "Full name and email are required.")
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
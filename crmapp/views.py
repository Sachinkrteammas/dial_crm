from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render, redirect
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

    return render(request, 'crmapp/user_list.html')


def user_list_api(request):
    users = UserList.objects.all().order_by('id').values(
        'id', 'full_name', 'user_role', 'email_id', 'company', 'contact_no'
    )
    return JsonResponse({'data': list(users)})
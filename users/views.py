from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from .form import UserRegistrationForm, UserLoginForm, UserResetPasswordForm, UserEditProfileForm, UserChangePasswordForm, UserDeleteAccountForm
# Create your views here.

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            confirm_password = form.cleaned_data['confirm_password']

            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, 'users/register.html', {'form': form})

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
                return render(request, 'users/register.html', {'form': form})

            if User.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
                return render(request, 'users/register.html', {'form': form})

            user = User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, "Registration successful.")
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('profile')
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()
    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def profile(request):

    return render(request, 'users/profile.html')

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserEditProfileForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']

            user = request.user
            if username != user.username and User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
                return render(request, 'users/edit_profile.html', {'form': form})
            if email != user.email and User.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
                return render(request, 'users/edit_profile.html', {'form': form})

            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = UserEditProfileForm(initial={
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        })
    return render(request, 'users/edit_profile.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = UserChangePasswordForm(request.POST)
        if form.is_valid():
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password']
            confirm_new_password = form.cleaned_data['confirm_new_password']

            if not request.user.check_password(old_password):
                messages.error(request, "Current password is incorrect.")
                return render(request, 'users/change_password.html', {'form': form})

            if new_password != confirm_new_password:
                messages.error(request, "New passwords do not match.")
                return render(request, 'users/change_password.html', {'form': form})

            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, "Password changed successfully. Please login again.")
            return redirect('login')
    else:
        form = UserChangePasswordForm()
    return render(request, 'users/change_password.html', {'form': form})

@login_required
def delete_account(request):
    if request.method == 'POST':
        form = UserDeleteAccountForm(request.POST)
        if form.is_valid():
            confirm_password = form.cleaned_data['confirm_password']
            if request.user.check_password(confirm_password):
                user = request.user
                logout(request)
                user.delete()
                messages.success(request, "Account deleted successfully.")
                return redirect('register')
            else:
                messages.error(request, "Incorrect password.")
                return render(request, 'users/delete_account.html', {'form': form})
    else:
        form = UserDeleteAccountForm()
    return render(request, 'users/delete_account.html', {'form': form})

def reset_password(request):
    if request.method == 'POST':
        form = UserResetPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']

            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_link = request.build_absolute_uri(f'/reset-password/confirm/{uid}/{token}/')

                send_mail(
                    'Password Reset Request',
                    f'Hi {first_name} {last_name},\n\nYou requested a password reset. Click the link below to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this email.',
                    'from@example.com',
                    [email],
                )
            except User.DoesNotExist:
                messages.error(request, "No user found with that email address.")
    return render(request, 'users/reset_password.html')

def reset_password_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    return render(request, 'users/reset_password_confirm.html')
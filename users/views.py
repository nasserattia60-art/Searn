from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from .form import (
    UserRegistrationForm, UserLoginForm, UserResetPasswordForm,
    UserEditProfileForm, UserChangePasswordForm, UserDeleteAccountForm,
    UserSetNewPasswordForm,
)


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

            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, "Registration successful. Please login.")
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    next_url = request.POST.get('next') or request.GET.get('next') or 'profile'

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect(next_url)
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form, 'next': next_url})


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
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password changed successfully.")
            return redirect('profile')
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
                reset_link = request.build_absolute_uri(
                    f'/users/reset-password/confirm/{uid}/{token}/'
                )

                send_mail(
                    'Password Reset Request',
                    f'Hi {first_name} {last_name},\n\n'
                    f'You requested a password reset. Click the link below to reset your password:\n'
                    f'{reset_link}\n\n'
                    f'If you did not request this, please ignore this email.',
                    'noreply@searn.com',
                    [email],
                )
                messages.success(
                    request,
                    "If an account with that email exists, a password reset link has been sent."
                )
            except User.DoesNotExist:
                messages.success(
                    request,
                    "If an account with that email exists, a password reset link has been sent."
                )
            return redirect('login')
    else:
        form = UserResetPasswordForm()

    return render(request, 'users/reset_password.html', {'form': form})


def reset_password_confirm(request, uidb64, token):
    reset_user = None

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        reset_user = User.objects.get(pk=uid)

        if not default_token_generator.check_token(reset_user, token):
            reset_user = None
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        reset_user = None

    if request.method == 'POST' and reset_user is not None:
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')

        if not new_password or len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        elif new_password != confirm_new_password:
            messages.error(request, "Passwords do not match.")
        else:
            reset_user.set_password(new_password)
            reset_user.save()
            messages.success(request, "Password has been reset successfully. Please login.")
            return redirect('login')

    return render(request, 'users/reset_password_confirm.html', {
        'reset_user': reset_user,
    })
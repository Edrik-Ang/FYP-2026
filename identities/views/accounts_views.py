## identities/views/accounts_views.py handles web facing views for account management, including email change, password change, and account deletion.
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render

from ..serializers import EmailChangeSerializer, PasswordChangeSerializer, AccountDeleteSerializer
from ..services.account_service import AccountService

@login_required
def email_change_view(request):
    if request.method == 'POST':
        serializer = EmailChangeSerializer(data=request.POST, context={'request': request})
        if serializer.is_valid():
            AccountService.change_email(request.user, serializer.validated_data['email'])
            messages.success(request, "Email updated.")
            return redirect('account-settings')
        return render(request, 'identities/account_settings.html', {
            'profile': request.user.profile,
            'email_errors': serializer.errors})
    return redirect('account-settings')


@login_required
def password_change_view(request):
    if request.method == 'POST':
        serializer = PasswordChangeSerializer(data=request.POST, context={'request': request})
        if serializer.is_valid():
            AccountService.change_password(request.user, serializer.validated_data['new_password'])
            # keeps the current session valid post-password-change instead of
            # forcing Django's default logout-on-password-change behaviour
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password updated.")
            return redirect('account-settings')
        return render(request, 'identities/account_settings.html', {
            'profile': request.user.profile,
            'password_errors': serializer.errors})
    return redirect('account-settings')


@login_required
def account_delete_view(request):
    if request.method == 'POST':
        serializer = AccountDeleteSerializer(data=request.POST, context={'request': request})
        if serializer.is_valid():
            AccountService.delete_account(request.user)
            logout(request)
            messages.success(request, "Your account has been deleted.")
            return redirect('home')
        return render(request, 'identities/account_settings.html', {
            'profile': request.user.profile,
            'delete_errors': serializer.errors})
    return redirect('account-settings')
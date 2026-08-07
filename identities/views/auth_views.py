## auth_views.py file handles the authentication views for login, registration, and logout functionality.
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from ..serializers import RegisterSerializer
from ..services.auth_service import AuthService

class WebLoginView(LoginView):
    template_name = 'identities/login.html'
    redirect_authenticated_user = True


class WebLogoutView(LogoutView):
    next_page = reverse_lazy('login')


def register_view(request):
    if request.method == 'POST':
        serializer = RegisterSerializer(data=request.POST)
        if serializer.is_valid():
            user = AuthService.register_user(serializer)
            login(request, user) ## uses Django's built in login function to log user in after registration
            return redirect('dashboard')
        return render(request, 'identities/register.html', {'errors': serializer.errors})
    return render(request, 'identities/register.html')

## auth_views.py file handles the authentication views for login, registration, and logout functionality.
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from ..serializers import RegisterSerializer

class WebLoginView(LoginView):
    template_name = 'identities/login.html'
    redirect_authenticated_user = True


class WebLogoutView(LogoutView):
    next_page = reverse_lazy('login')


def register_view(request):
    if request.method == 'POST':
        serializer = RegisterSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user) ## uses Django's built in login function to log user in after registration
            return redirect('dashboard')
        return render(request, 'identities/register.html', {'errors': serializer.errors})
    return render(request, 'identities/register.html')

# def login_view(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             login(request, user)
#             return redirect('dashboard')
#         return render(request, "login.html", {"error": "Invalid username or password"})
#     return render(request, 'login.html')


# def register_view(request):
#     if request.method == 'POST':
#         serializer = RegisterSerializer(data=request.POST)
#         if serializer.is_valid():
#             user = serializer.save()
#             login(request, user)
#             return redirect('dashboard')
#         return render(request, 'register.html', {'errors': serializer.errors})
#     return render(request, 'register.html')


# def logout_view(request):
#     logout(request)
#     return redirect('login')
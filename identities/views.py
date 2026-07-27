## views.py file for identities app.
## handles the routing and logic of urls to correct views
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, get_user_model, login, logout
from .serializers import RegisterSerializer
from .models import *
from .disclosure import get_effective_contexts, get_visible_fields

User = get_user_model()

##Default page view for application, quite basic first, will improve later
def home_view(request):
    return render(request, 'home.html')

###login_view function, page to view the login form for existing users
def login_view(request):
    #print("login_view reached")
    #print("Request method:", request.method)
    if request.method == 'POST':
        #print("POST data:", request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        #print("Username:", username)
        #print("Password:", bool(password))
        
        user = authenticate(
            request, 
            username=username, 
            password=password
        )
        #print("Authenticated user:", user)
        if user is not None:
            login(request, user)
            #print("Login successful for user:", user.username)
            return redirect('dashboard')
        else:
            print("Login failed for user:", username)
            return render(
                request,
                "login.html",
                {
                    "error": "Invalid username or password"
                }
            )
    return render(request, 'login.html')


### Dashboard when user log in, for now shows all the users in system.
@login_required
def dashboard_view(request):
    users = User.objects.exclude(id=request.user.id)
    identities = IdentityProfile.objects.filter(owner=request.user)

    return render(
        request, 
        "dashboard.html",
        {
            "users":users,
            "identities":identities
        }
    )
##logout_view function, logs out the user and redirects to login page
@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

##When a user search for a profile, this will redirect to profile view of the user searched for.
@login_required
def profile_redirect_view(request):
    username = request.GET.get('username')
    if not username:
        return redirect("dashboard")
    return redirect('profile', username=username)

### register_view function, page to view the registration form for new users
def register_view(request):
    if request.method == 'POST':
        serializer = RegisterSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user) # log them in after registration
            return redirect('dashboard')
        return render(request, 'register.html', {'errors': serializer.errors})
    return render(request, 'register.html')


# Create your views here.
### profile_view function
### retrieves the profile of a user based on the username provided in the URL
@login_required
def profile_view(request, username):
    owner = get_object_or_404(User, username=username)
    identities = IdentityProfile.objects.filter(owner=owner)

    if owner == request.user:
        visible_data =[
            {f:getattr(identity,field) for field, _ in DisclosureRule.FIELD_CHOICES} for identity in identities
        ]
    else:
        viewer_contexts = get_effective_contexts(owner, request.user)
        visible_data = []
        for identity in identities:
            fields = get_visible_fields(identity, viewer_contexts)
            if fields:
                visible_data.append({f: getattr(identity, f) for f in fields})
    return render(
        request,
        'profile.html',
        {
            'owner': owner,
            'visible_data': visible_data
        }
    )
    


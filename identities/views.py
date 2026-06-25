from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from .models import *

User = get_user_model()

##Default page view for application, quite basic first, will improve later
def home_view(request):
    return render(request, 'home.html')

###login_view function, page to view the login form for existing users
def login_view(request):
    return render(request, 'login.html')

### register_view function, page to view the registration form for new users
def register_view(request):
    return render(request, 'register.html')

# Create your views here.
### profile_view function
### retrieves the profile of a user based on the username provided in the URL
def profile_view(request, username):
    owner = get_object_or_404(User, username=username)

    try:
        relationship = Relationship.objects.get(
            owner=owner,
            target_user=request.user
        )
        rel_type = relationship.relationship_type
    except Relationship.DoesNotExist:
        rel_type = None
    
    # Owner identities
    identities = IdentityProfile.objects.filter(owner=owner)

    visible_data = []
    for identity in identities:
        allowed_fields = DisclosureRule.objects.filter(
            identity=identity,
            relationship_type=rel_type,
            is_visible=True
        ).values_list('field_name', flat=True)

        filtered_identity = {}
        for field in allowed_fields:
            filtered_identity[field] = getattr(identity, field)
        visible_data.append(filtered_identity)
    return render(
        request, 
        'profile.html', 
        {
            'visible_data':visible_data
        }
    )
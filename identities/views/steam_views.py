### steam_views.py handles the web facing side of Steam integration, including login and callback views for linking Steam accounts to user profiles.
## If other integration views are added in the future, they will expand this file or be split into their own files as needed.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from identities.models import IdentityProfile, LinkedAccount
from identities.services.identity_service import IdentityService
from identities.security.error_handling import handle_integration_errors
from django.views.decorators.http import require_POST

from identities.services.steam_service import SteamService

STEAM_MATERIALIZE_FIELDS = ['summary', 'badges', 'owned_games', 'recent_games', 'wishlist']


@login_required
def steam_link_view(request):
    """View to link Steam account to the logged-in user."""
    return redirect(SteamService.build_auth_url(request))


@login_required
@handle_integration_errors('dashboard', 'Steam')  # Use the decorator for error handling
def steam_callback_view(request):
    """View to handle the callback verification from Steam after user authentication."""
    steam_id64 = SteamService.verify_callback(request)
    SteamService.link_steam_account(request.user, steam_id64)
    messages.success(request, "Steam account linked successfully.")
    return redirect("dashboard")

@login_required
@require_POST
def steam_unlink_view(request):
    """View to unlink Steam account from the logged-in user."""
    if request.method == "POST":
        SteamService.unlink_steam_account(request.user)
        messages.success(request, "Steam account unlinked successfully.")
    return redirect("dashboard")


@login_required
@require_POST
@handle_integration_errors('dashboard', 'Steam')  # Use the decorator for error handling
def steam_refresh_view(request):
    if request.method == "POST":
        SteamService.refresh_player_data(request.user)
        messages.success(request, "Steam player data refreshed successfully.")
    return redirect("dashboard")


@login_required
def steam_profile_view(request):
    """View to display Steam profile information for logged in user. 
    Allow user to pick  an identity by checkboxing which fields to materialize.
    """
    linked_account = get_object_or_404(LinkedAccount, user=request.user, provider='steam')
    identities = IdentityService.list_identities(request.user)

    if request.method == 'POST':
        identity = IdentityProfile.objects.filter(pk=request.POST.get('identity_id'), owner=request.user).first()
        if not identity:
            messages.error(request, "Please select a valid identity.")
            return redirect('steam-profile')
        
        for field in request.POST.getlist('fields'):
            if field in STEAM_MATERIALIZE_FIELDS:
                IdentityService.set_attribute(identity, key=field, value=linked_account.raw_data.get(field), source='steam')
        messages.success(request, f"Steam data added to '{identity.identity_name}'.")
        return redirect('steam-profile')

    identity_steam_data = [
        (identity, list(identity.attributes.filter(source='steam').values_list('key', flat=True)))
        for identity in identities
    ]

    return render(request, 'identities/steam_profile.html',{
        'linked_account': linked_account,
        'identities': identities,
        'identity_steam_data': identity_steam_data,
    })
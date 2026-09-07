## identities/views/integration_views.py
## Web-facing views for external account integrations (Steam, and later GitHub/YouTube).
## Thin views: session-auth only, delegate all business logic to SteamService / IdentityService.

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from rest_framework.exceptions import ValidationError

from identities.models import LinkedAccount, IdentityProfile
from identities.services.steam_service import SteamService
from identities.services.identity_service import IdentityService


# Steam raw_data keys that are safe to materialize onto an IdentityAttribute.
# Mirrors the checkboxes rendered in steam_profile.html.
STEAM_MATERIALIZABLE_FIELDS = ('summary', 'badges', 'owned_games', 'recent_games', 'wishlist')


@login_required
def steam_link_view(request):
    """ Redirects the user to Steam's OpenID login page to begin the linking handshake. """
    auth_url = SteamService.build_auth_url(request)
    return redirect(auth_url)


@login_required
def steam_callback_view(request):
    """
    Steam redirects the browser back here after login. Verifies the handshake,
    then links the resulting SteamID64 to the current user's LinkedAccount.
    """
    try:
        steamid64 = SteamService.verify_callback(request)
        SteamService.link_steam_account(request.user, steamid64)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('dashboard')

    messages.success(request, "Steam account linked successfully.")
    return redirect('steam-profile')


@login_required
@require_POST
def steam_unlink_view(request):
    """ Unlinks the current user's Steam account. Does not remove already-materialized IdentityAttributes. """
    SteamService.unlink_steam_account(request.user)
    messages.success(request, "Steam account unlinked.")
    return redirect('dashboard')


@login_required
@require_POST
def steam_refresh_view(request):
    """ Re-fetches Steam profile data for the currently linked account. """
    try:
        SteamService.refresh_player_data(request.user)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('dashboard')

    messages.success(request, "Steam data refreshed.")
    return redirect('steam-profile')


@login_required
def steam_profile_view(request):
    """
    GET: shows the linked Steam account's fetched data, and a form to materialize
    selected fields onto one of the user's identities.
    POST: materializes the selected fields (from raw_data) onto the chosen identity
    as IdentityAttribute rows with source='steam', so DisclosureRules can reference them.
    """
    linked_account = get_object_or_404(LinkedAccount, user=request.user, provider='steam')
    identities = IdentityService.list_identities(request.user)

    if request.method == 'POST':
        identity_id = request.POST.get('identity_id')
        # Ownership check: identity must belong to the current user, same guard style as other web views.
        identity = get_object_or_404(IdentityProfile, pk=identity_id, owner=request.user)

        selected_fields = [f for f in request.POST.getlist('fields') if f in STEAM_MATERIALIZABLE_FIELDS]
        for field in selected_fields:
            value = linked_account.raw_data.get(field)
            if value:
                IdentityService.set_attribute(identity, field, value, source='steam')

        if selected_fields:
            messages.success(request, f"Added {', '.join(selected_fields)} to {identity.identity_name}.")
        return redirect('steam-profile')

    # Build "Currently exposed Steam data" summary: for each identity, which of its
    # materialized attribute keys came from Steam.
    identity_steam_data = [
        (identity, list(
            IdentityService.list_attributes(identity).filter(source='steam').values_list('key', flat=True)
        ))
        for identity in identities
    ]

    return render(request, 'identities/steam_profile.html', {
        'linked_account': linked_account,
        'identities': identities,
        'identity_steam_data': identity_steam_data,
    })
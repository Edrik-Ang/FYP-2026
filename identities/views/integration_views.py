### integration_views.py handles the web facing side of Steam integration, including login and callback views for linking Steam accounts to user profiles.
## If other integration views are added in the future, they will expand this file or be split into their own files as needed.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from rest_framework.exceptions import ValidationError

from identities.services.steam_service import SteamService


@login_required
def steam_link_view(request):
    """View to link Steam account to the logged-in user."""
    return redirect(SteamService.build_auth_url(request))


@login_required
def steam_callback_view(request):
    """View to handle the callback verification from Steam after user authentication."""
    try:
        steam_id64 = SteamService.verify_callback(request)
        SteamService.link_steam_account(request.user, steam_id64)
        messages.success(request, "Steam account linked successfully.")
    except ValidationError as e:
        detail = e.detail[0] if isinstance(e.detail, list) else e.detail
        messages.error(request, f"Error linking Steam account: {detail}")
    return redirect("dashboard")


def steam_unlink_view(request):
    """View to unlink Steam account from the logged-in user."""
    if request.method == "POST":
        SteamService.unlink_steam_account(request.user)
        messages.success(request, "Steam account unlinked successfully.")
    return redirect("dashboard")
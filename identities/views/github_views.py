## github_views.py -- web facing views for Github integration.
## has loginc redirects + callback verfications
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from rest_framework.exceptions import ValidationError

from identities.services.github_service import GithubService


@login_required
def github_link_view(request):
    """ View to link githuub account to logged-in user."""
    return redirect(GithubService.build_auth_url(request))


@login_required
def github_callback_view(request):
    """View to handle callback from Github after user authorization. """
    try:
        token_data = GithubService.verify_callback(request)
        GithubService.link_github_account(request.user, token_data)
        messages.success(request, "Github account linked successfully.")
    except ValidationError as e:
        # Validation errors may contain either one message or a list of messages.
        if isinstance(e.detail, list):
            detail = e.detail[0]
        else:
            detail = e.detail
        messages.error(request, f"Error linking Github account: {detail}")
    return redirect('dashboard')

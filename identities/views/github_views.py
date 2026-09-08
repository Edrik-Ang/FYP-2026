## github_views.py -- web facing views for Github integration.
## has loginc redirects + callback verfications
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from rest_framework.exceptions import ValidationError

from identities.models import IdentityProfile, LinkedAccount
from identities.services.github_service import GITHUB_MATERIALIZE_FIELDS, GithubService
from identities.services.identity_service import IdentityService


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

@login_required
def github_profile_view(request):
    """View to display Github profile information for logged-in user, and materialize
    selected fields to a chosen identity as IdentityAttribute rows."""
    linked_account = get_object_or_404(LinkedAccount, user=request.user, provider='github')
    identities = IdentityService.list_identities(request.user)

    if request.method == 'POST':
        identity = IdentityProfile.objects.filter(pk=request.POST.get('identity_id'), owner=request.user).first()
        if not identity:
            messages.error(request, "Invalid identity selected.")
            return redirect('github-profile')

        for field in request.POST.getlist('fields'):
            if field in GITHUB_MATERIALIZE_FIELDS:
                IdentityService.set_attribute(identity, key=field, value=linked_account.raw_data.get(field), source='github')
        messages.success(request, f"GitHub data added to '{identity.identity_name}'.")
        return redirect('github-profile')

    identity_github_data = [
        (identity, list(identity.attributes.filter(source='github').values_list('key', flat=True)))
        for identity in identities
    ]
    return render(request, 'identities/github_profile.html', {
        'linked_account': linked_account,
        'identities': identities,
        'identity_github_data': identity_github_data,
    })


@login_required
def github_unlink_view(request):
    """View to unlink Github account from logged-in user."""
    if request.method == 'POST':
        GithubService.unlink_github_account(request.user)
        messages.success(request, "Github account unlinked successfully.")
    return redirect('dashboard')


@login_required
def github_refresh_view(request):
    """view to refresh Github access token for logged-in user."""
    if request.method == 'POST':
        try:
            GithubService.refresh_github_token(request.user)
            messages.success(request, "Github access token refreshed successfully.")
        except ValidationError as e:
            detail = e.detail[0] if isinstance(e.detail, list) else e.detail
            messages.error(request, str(detail))
    return redirect('dashboard')

## github_views.py -- web facing views for Github integration.
## has loginc redirects + callback verfications
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from identities.services.github_service import GithubService


@login_required
def github_link_view(request):
    """ View to link githuub account to logged-in user."""
    return redirect(GithubService.build_auth_url(request))


@login_required
def github_callback_view(request):
    """Basic stub for now, will call verify_callback and link_github_account in the future."""
    return redirect('dashboard')

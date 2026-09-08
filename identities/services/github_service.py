## services/github_service.py 
## handles GitHub API interactions
## refer to https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps for OAuth2 flow
from urllib.parse import urlencode

from django.urls import reverse
from django.conf import settings
import requests
import secrets
from rest_framework.exceptions import ValidationError

from identities.models import LinkedAccount


class GithubService:
    """ Handles the communication with GitHub's API for user authentication and data retrieval.
    OAuth 2.0 authorisation flow and links to veerified GitHub account to currenlty logged in user's LinkedAccount.
    """

    @staticmethod
    def build_auth_url(request):
        """ builds the Github's redirect URL for OAuth2 authorisation 
        and stash the anti-CSRF 'state' value in session. Steam Nonce equivalent basically.
        Returns a full URL to redirect user to GitHub for authorisation."""
        state = secrets.token_urlsafe(24)
        request.session['github_auth_state'] = state
        redirect_url = request.build_absolute_uri(reverse('github-callback'))
        params = {
            'client_id': settings.GITHUB_CLIENT_ID,
            'redirect_uri': redirect_url,
            'scope': 'read:user',
            'state': state
        }
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    @staticmethod
    def verify_callback(request):
        """ verifies the 'state' param against session (CSRF check), then exchanges the 'code' github sent back for access_token 
        return dict: {'access_token': 'refresh_token', 'expires_in'}. Raises ValidationError on any failure.
        """
        params = request.GET
        expected_state = request.session.pop('github_auth_state', None)
        if not expected_state or params.get('state') != expected_state:
            raise ValidationError("Github login session expired or invalid. Please try again.")
        code = params.get('code')
        if not code:
            raise ValidationError("Github login was not completed successfully. Please try again")

        redirect_uri = request.build_absolute_uri(reverse('github-callback'))
        response = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                'client_id': settings.GITHUB_CLIENT_ID,
                'client_secret': settings.GITHUB_CLIENT_SECRET,
                'code': code,
                'redirect_uri': redirect_uri,
            },
            headers={'Accept': 'application/json'},
            timeout=10,
        )
        response.raise_for_status()
        token_data = response.json()

        if 'access_token' not in token_data:
            raise ValidationError("Github could not verify this login attempt. Please try again.")

        return token_data
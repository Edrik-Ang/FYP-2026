## services/github_service.py 
## handles GitHub API interactions
## refer to https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps for OAuth2 flow
from urllib.parse import urlencode

from django.db import IntegrityError
from django.urls import reverse
from django.conf import settings
import requests
import secrets
from django.utils import timezone
from datetime import timedelta
from rest_framework.exceptions import ValidationError

from identities.models import LinkedAccount

GITHUB_MATERIALIZE_FIELDS = ['login', 'name', 'avatar_url', 'html_url', 'bio', 'company', 'location']

class GithubService:
    """ Handles the communication with GitHub's API for user authentication and data retrieval.
    OAuth 2.0 authorisation flow and links to veerified GitHub account to currenlty logged in user's LinkedAccount.
    """

    @staticmethod
    def build_auth_url(request):
        """ builds the Github's redirect URL for OAuth2 authorisation 
        and stash the anti-CSRF 'state' value in session. Steam Nonce equivalent basically.
        Returns a full URL to redirect user to GitHub for authorisation."""
        url = "https://github.com/login/oauth/authorize"
        state = secrets.token_urlsafe(24)
        request.session['github_auth_state'] = state
        redirect_url = request.build_absolute_uri(reverse('github-callback'))
        params = {
            'client_id': settings.GITHUB_CLIENT_ID,
            'redirect_uri': redirect_url,
            'scope': 'read:user',
            'state': state
        }
        return f"{url}?{urlencode(params)}"

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

    @staticmethod
    def fetch_profile_data(access_token):
        """ Uses access_token to fetch authenticated user public profile from Github's /user endpoint. 
        fetches fields that are useful or sensitive to materialize into our system.
        Returns the fields of interest, 'id' and 'login' (needed for provider_uid, not for disclosure.)"""
        try:
            response = requests.get(
                "https://api.github.com/user",
                headers={
                    'Authorization': f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                timeout=10, ## timeout after 10 seconds, to avoid hanging the request
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            raise ValidationError("Unable to retrieve your Github profile. Please try again.")

        return{ ## will be the profile data stored in LinkedAccount.raw_data, but only the fields we care about for now.
            'id': data.get('id'), 
            'login': data.get('login'),
            'avatar_url': data.get('avatar_url'),
            'html_url': data.get('html_url'),
            'name': data.get('name'),
            'bio': data.get('bio'),
            'company': data.get('company'),
            'location': data.get('location'),
        }

    @staticmethod
    def link_github_account(user, token_data):
        """ Links a verified Github account to currently logged in user's LinkedAccount.
        Raises validationError if this Github account already linked to another user, or if the user already has a linked Github account."""
        access_token = token_data.get('access_token')
        profile = GithubService.fetch_profile_data(access_token)
        github_id = profile.get('id') ## better since login can change, but id is stable. will use this as provider_uid in LinkedAccount.

        if not github_id:
            raise ValidationError("Couldnt get Github profile, please try again.")

        existing = LinkedAccount.objects.filter(provider='github', provider_uid=github_id).first()
        if existing and existing.user_id != user.id:
            raise ValidationError("This Github account is already linked to another user.")

        expires_in = token_data.get('expires_in')
        token_expires_at = (
            timezone.now() + timedelta(seconds=expires_in) if expires_in else None
        )
        try: 
            account, _ = LinkedAccount.objects.update_or_create(
                user=user, 
                provider='github',
                defaults={
                    'provider_uid':github_id,
                    'access_token': access_token, 
                    'refresh_token': token_data.get('refresh_token'),
                    'token_expires_at': token_expires_at,
                    'raw_data': profile,
                },
            )
        except IntegrityError:
            raise ValidationError("This user already has a linked Github account.")\
            
        return account


    @staticmethod
    def unlink_github_account(user):
        """ Unlinks the Github account from the currently authenticated user LinkedAccount.
        """
        LinkedAccount.objects.filter(user=user, provider='github').delete()


    @staticmethod
    def refresh_github_token(user):
        """ Refetches profile data for an already linked Github accounnt, using stored access_token. If expired, the API call will 401
        reutnrs as ValidationError than a raw exception, since automatic token refresh not implemented yet. 
        """
        account = LinkedAccount.objects.filter(user=user, provider='github').first()
        if not account:
            raise ValidationError("No linked Github to refresh. ")

        if account.token_expires_at and account.token_expires_at <= timezone.now():
            raise ValidationError("Your Github session has expired. Please unlink and relink your account.")
        profile = GithubService.fetch_profile_data(account.access_token)
        account.raw_data = profile
        account.save(update_fields=['raw_data'])
        return account
    
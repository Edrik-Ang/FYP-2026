import secrets
from urllib.parse import urlencode

import requests
from django.db import IntegrityError
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from xml.etree import ElementTree
from django.conf import settings

from identities.models import LinkedAccount

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
STEAM_CLAIMED_ID_PREFIX = "https://steamcommunity.com/openid/id/"
STEAM_PLAYER_SUMMARY_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
STEAM_XML_PROFILE_URL = "https://steamcommunity.com/profiles/{steamid64}?xml=1"


class SteamService:
    """
    Handles Steam OpenID 2.0 handskake and links a verified SteamID 64 ot currently authenticated user's LinkedAccount.
    Depends on Django's session (not JWT): Steam's redirect to callback is plain browser GET, 
    so request.user only available because web routes already authenticate via session cookie across redirects.
    """

    @staticmethod
    def build_auth_url(request):
        """ Builds Steam login redirect URL and stashes an anti CSRF nonce in session. Returns the URL to redirect the user to Steam for login. """
        nonce = secrets.token_urlsafe(24)
        request.session['steam_auth_nonce'] = nonce

        return_to = request.build_absolute_uri(reverse('steam-callback')) + f"?nonce={nonce}"
        realm = request.build_absolute_uri('/')
        params = {
            'openid.ns': 'http://specs.openid.net/auth/2.0',
            'openid.mode': 'checkid_setup',
            'openid.return_to': return_to,
            'openid.realm': realm,
            'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select',
        }
        return f"{STEAM_OPENID_URL}?{urlencode(params)}"

    @staticmethod
    def verify_callback(request):
        """
        Verifies Steam's callback params against Steam Itself (check_authentication)
        Takes in the request from Steam's callback
        and checks the anti CSRF nonce. Returns the verified SteamID64.
        Raises ValidationError if verification fails.
        """
        params = request.GET
        expected_nonce = request.session.pop('steam_auth_nonce', None)
        if not expected_nonce or params.get('nonce') != expected_nonce:
            raise ValidationError("Steam login session expired or invalid. Please try again.")
        if params.get('openid.mode') != 'id_res':
            raise ValidationError("Steam login was not completed successfully. Please try again.")

        verify_params= params.dict()
        verify_params['openid.mode'] = 'check_authentication'
        response = requests.post(STEAM_OPENID_URL, data=verify_params, timeout=10)
        if 'is_valid:true' not in response.text:
            raise ValidationError("Steam could not verify this login attempt. Please try again.")

        claimed_id = params.get('openid.claimed_id','')
        if not claimed_id.startswith(STEAM_CLAIMED_ID_PREFIX):
            raise ValidationError("Unexpected response from Steam.")

        return claimed_id.removeprefix(STEAM_CLAIMED_ID_PREFIX)


    @staticmethod
    def link_steam_account(user, steamid64, raw_data=None):
        """
        Links a verified SteamID64 to the currently authenticated user's LinkedAccount.
        Takes in user, steamid64, and optional raw_data (dict) from Steam API. Raises ValidationError if the SteamID is already linked to another user.
        """
        existing = LinkedAccount.objects.filter(provider='steam', provider_uid=steamid64).first()
        if existing and existing.user != user.id:
            raise ValidationError("This Steam account is already linked to another user.")

        try:
            raw_data = SteamService.fetch_player_summary(steamid64)
        except Exception:
            raw_data = {}
        try: 
            account, _ = LinkedAccount.objects.update_or_create(
                user=user, provider='steam', 
                defaults={'provider_uid': steamid64, 'raw_data': raw_data or {}},
            )

        except IntegrityError:
            raise ValidationError("This Steam account is already linked to another user.")
        return account


    @staticmethod
    def unlink_steam_account(user):
        """
        Unlinks the Steam account from the currently authenticated user's LinkedAccount.
        """
        LinkedAccount.objects.filter(user=user, provider='steam').delete()


    @staticmethod
    def refresh_player_data(user):
        """
        Re-fetches profile data for an already linked Steam account
        """
        account = LinkedAccount.objects.filter(user=user, provider='steam').first()
        if not account:
            raise ValidationError("No linked Steam account to refresh.")
        account.raw_data = SteamService.fetch_player_summary(account.provider_uid)
        account.save(update_fields=['raw_data'])
        return account
        
    # https://partner.steamgames.com/doc/webapi/isteamuser 
    @staticmethod
    def fetch_player_summary(steamid64):
        """
        Uses Official ISteamUser /GetPlayerSummaries endpoint. summary (about me) is not part of this response 
        -- fetched separately using Steam's unoffical XML profile feed and best-effort parsing. (empty string on failure)
        """
        response = requests.get(STEAM_PLAYER_SUMMARY_URL, params={
            'key': settings.STEAM_API_KEY,
            'steamids': steamid64,
        }, timeout=10)
        response.raise_for_status()
        players = response.json().get('response', {}).get('players', [])
        if not players:
            raise ValidationError("Steam profile not found or private.")
        player = players[0]

        return {
            'personaname': player.get('personaname', ''),
            'profileurl': player.get('profileurl', ''),
            'avatar': player.get('avatar', ''),
            'avatarmedium': player.get('avatarmedium', ''),
            'avatarfull': player.get('avatarfull', ''),
            'is_public':player.get('communityvisibilitystate') == 3,
            'summary': SteamService._fetch_profile_summary(steamid64),
        }


    @staticmethod
    def _fetch_profile_summary(steamid64): ## for the about me summary.
        try:
            response = requests.get(STEAM_XML_PROFILE_URL.format(steamid64=steamid64), timeout=10)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
            summary_el = root.find('summary')
            return summary_el.text.strip() if summary_el is not None and summary_el.text else ''
        except Exception:
            return ''

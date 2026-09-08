from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, RequestFactory
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from identities.models import LinkedAccount, IdentityProfile, Context
from identities.services.steam_service import SteamService

User = get_user_model()


class SteamServiceVerifyCallbackTests(TestCase):
    """
    Tests the logic that runs *after* Steam redirects back -- nonce checking
    and the check_authentication round trip. Mocks requests.post so no real
    call to Steam happens. This is the part of the OpenID flow that IS
    testable; the actual browser redirect to Steam's login page is not.
    """

    def _build_request(self, get_params, nonce_in_session='abc123'):
        request = RequestFactory().get('/integrations/steam/callback/', get_params)
        request.session = {}
        if nonce_in_session:
            request.session['steam_auth_nonce'] = nonce_in_session
        return request

    @patch('identities.services.steam_service.requests.post')
    def test_valid_callback_returns_steamid(self, mock_post):
        mock_post.return_value = Mock(text='is_valid:true')
        request = self._build_request({
            'nonce': 'abc123',
            'openid.mode': 'id_res',
            'openid.claimed_id': 'https://steamcommunity.com/openid/id/76561198012345678',
        })
        self.assertEqual(SteamService.verify_callback(request), '76561198012345678')

    def test_missing_nonce_raises(self):
        request = self._build_request({'openid.mode': 'id_res'}, nonce_in_session=None)
        with self.assertRaises(ValidationError):
            SteamService.verify_callback(request)

    @patch('identities.services.steam_service.requests.post')
    def test_failed_steam_verification_raises(self, mock_post):
        mock_post.return_value = Mock(text='is_valid:false')
        request = self._build_request({
            'nonce': 'abc123',
            'openid.mode': 'id_res',
            'openid.claimed_id': 'https://steamcommunity.com/openid/id/76561198012345678',
        })
        with self.assertRaises(ValidationError):
            SteamService.verify_callback(request)


class SteamServiceLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.other_user = User.objects.create_user(username='bob', password='pass12345')

    @patch('identities.services.steam_service.SteamService.fetch_player_summary')
    def test_link_creates_linked_account(self, mock_fetch):
        mock_fetch.return_value = {'personaname': 'AliceGamer'}
        account = SteamService.link_steam_account(self.user, '76561198000000001')
        self.assertEqual(account.provider_uid, '76561198000000001')
        self.assertEqual(account.raw_data['personaname'], 'AliceGamer')

    @patch('identities.services.steam_service.SteamService.fetch_player_summary')
    def test_link_to_already_claimed_steamid_raises(self, mock_fetch):
        mock_fetch.return_value = {}
        LinkedAccount.objects.create(user=self.other_user, provider='steam', provider_uid='76561198000000001')
        with self.assertRaises(ValidationError):
            SteamService.link_steam_account(self.user, '76561198000000001')

    @patch('identities.services.steam_service.SteamService.fetch_player_summary')
    def test_relinking_same_user_overwrites_not_duplicates(self, mock_fetch):
        mock_fetch.return_value = {}
        SteamService.link_steam_account(self.user, '76561198000000001')
        SteamService.link_steam_account(self.user, '76561198000000002')
        self.assertEqual(LinkedAccount.objects.filter(user=self.user).count(), 1)


class SteamServiceFetchOwnedGamesTests(TestCase):
    @patch('identities.services.steam_service.requests.get')
    def test_public_game_details_returns_sorted_games(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {
            'response': {'game_count': 2, 'games': [
                {'appid': 730, 'name': 'CS2', 'playtime_forever': 500, 'img_icon_url': 'a'},
                {'appid': 570, 'name': 'Dota 2', 'playtime_forever': 100, 'img_icon_url': 'b'},
            ]}
        })
        result = SteamService._fetch_owned_games('765')
        self.assertTrue(result['visible'])
        self.assertEqual(result['games'][0]['name'], 'CS2')  # highest playtime first

    @patch('identities.services.steam_service.requests.get')
    def test_private_game_details_returns_not_visible(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {'response': {}})
        result = SteamService._fetch_owned_games('765')
        self.assertFalse(result['visible'])

    @patch('identities.services.steam_service.requests.get', side_effect=Exception('network error'))
    def test_network_failure_degrades_gracefully_instead_of_raising(self, mock_get):
        result = SteamService._fetch_owned_games('765')
        self.assertFalse(result['visible'])


class SteamServiceWishlistTests(TestCase):
    def tearDown(self):
        cache.delete('steam_app_name_lookup')

    @patch('identities.services.steam_service.requests.get')
    def test_wishlist_resolves_names_from_cached_lookup(self, mock_get):
        cache.set('steam_app_name_lookup', {39210: 'FINAL FANTASY XV'}, 3600)
        mock_get.return_value = Mock(status_code=200, json=lambda: {
            'response': {'items': [{'appid': 39210, 'priority': 1, 'date_added': 123}]}
        })
        result = SteamService._fetch_wishlist('765')
        self.assertEqual(result['items'][0]['name'], 'FINAL FANTASY XV')

    @patch('identities.services.steam_service.requests.get')
    def test_wishlist_falls_back_to_appid_when_name_unknown(self, mock_get):
        cache.set('steam_app_name_lookup', {}, 3600)
        mock_get.return_value = Mock(status_code=200, json=lambda: {
            'response': {'items': [{'appid': 99999, 'priority': 1, 'date_added': 123}]}
        })
        result = SteamService._fetch_wishlist('765')
        self.assertEqual(result['items'][0]['name'], 'App 99999')


class SteamIntegrationAPITests(APITestCase):
    """Tests the API view layer -- request/response contract, ownership checks,
    status codes. Mocks at the service boundary rather than the HTTP boundary,
    since service-level correctness is already covered above."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.other_user = User.objects.create_user(username='bob', password='pass12345')
        self.client.force_authenticate(user=self.user)
        self.context = Context.objects.create(owner=self.user, name='Gaming')
        self.identity = IdentityProfile.objects.create(owner=self.user, context=self.context, identity_name='Gamer Alice')

    def test_get_without_link_returns_404(self):
        response = self.client.get('/api/integrations/steam/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_see_another_users_linked_account(self):
        LinkedAccount.objects.create(user=self.other_user, provider='steam', provider_uid='999')
        response = self.client.get('/api/integrations/steam/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_materialize_writes_only_selected_and_valid_fields(self):
        LinkedAccount.objects.create(user=self.user, provider='steam', provider_uid='765', raw_data={
            'summary': 'hi', 'owned_games': {'games': []},
        })
        response = self.client.post('/api/integrations/steam/materialize/', {
            'identity_id': self.identity.id,
            'fields': ['summary', 'owned_games', 'not_a_real_field'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(response.data['materialized_fields'], ['summary', 'owned_games'])
        self.assertFalse(self.identity.attributes.filter(key='not_a_real_field').exists())

    def test_materialize_rejects_someone_elses_identity(self):
        LinkedAccount.objects.create(user=self.user, provider='steam', provider_uid='765', raw_data={'summary': 'hi'})
        other_context = Context.objects.create(owner=self.other_user, name='Other')
        other_identity = IdentityProfile.objects.create(owner=self.other_user, context=other_context, identity_name='Bob')
        response = self.client.post('/api/integrations/steam/materialize/', {
            'identity_id': other_identity.id, 'fields': ['summary'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unlink_removes_account(self):
        LinkedAccount.objects.create(user=self.user, provider='steam', provider_uid='765')
        response = self.client.delete('/api/integrations/steam/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LinkedAccount.objects.filter(user=self.user).exists())
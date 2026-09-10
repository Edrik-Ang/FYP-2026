## test_steam.py covers Steam integration in three layers:
##      # 1. SteamService in isolation, with request.get/request.post mocked -- no live
##           Steam calls, this is where almost all the meaningufl coverage live.
##      # 2. web-facing views (steam_views.py) via Django session-authenticated test client, with SteamService mocked out at the boundary os no network calls happen.
##      # 3. API views (api/api_steam.py) via DRF's APITestCase + force_authenticate, mirroring the web-view coverage for the JWT-facing surface.
## live OpenID handshake against Steam's real servers is not tested, because requires real browser session with cookies,
## but verify_callback's own logic (nonce check, mode check, check_authetnication call) can still be tested by mocking request.post and Django's session.
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.test import TestCase, RequestFactory
from django.urls import reverse

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from identities.models import Context, IdentityProfile, IdentityAttribute, LinkedAccount, DisclosureRule, Relationship
from identities.services.steam_service import SteamService
from identities.services.disclosure_service import DisclosureService

User = get_user_model()


def make_session_request(get_params=None, session_data=None):
    """ Builds a bare request with a real, saved session -- lets us test
    SteamService.verify_callback's nonce logic directly without going through
    a full view/client round trip. """
    factory = RequestFactory()
    request = factory.get('/integrations/steam/callback/', get_params or {})
    SessionMiddleware(lambda r: None).process_request(request)
    if session_data:
        request.session.update(session_data)
    request.session.save()
    return request


# ---------------------------------------------------------------------------
# SteamService -- data fetching methods (mocked HTTP)
# ---------------------------------------------------------------------------

class FetchOwnedGamesTests(TestCase):
    @patch('identities.services.steam_service.requests.get')
    def test_returns_games_sorted_by_playtime_desc(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {
            'response': {
                'game_count': 2,
                'games': [
                    {'appid': 10, 'name': 'Low Playtime', 'playtime_forever': 5},
                    {'appid': 20, 'name': 'High Playtime', 'playtime_forever': 500},
                ],
            }
        }
        result = SteamService._fetch_owned_games('76500000000000000')
        self.assertTrue(result['visible'])
        self.assertEqual(result['count'], 2)
        self.assertEqual([g['name'] for g in result['games']], ['High Playtime', 'Low Playtime'])

    @patch('identities.services.steam_service.requests.get')
    def test_private_game_details_returns_not_visible(self, mock_get):
        # Steam omits 'game_count' entirely (rather than erroring) when game details are private.
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {'response': {}}
        result = SteamService._fetch_owned_games('76500000000000000')
        self.assertFalse(result['visible'])
        self.assertEqual(result['games'], [])
        self.assertEqual(result['count'], 0)

    @patch('identities.services.steam_service.requests.get')
    def test_request_exception_returns_not_visible_rather_than_raising(self, mock_get):
        mock_get.side_effect = Exception("network error")
        result = SteamService._fetch_owned_games('76500000000000000')
        self.assertFalse(result['visible'])
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['games'], [])


class FetchRecentGamesTests(TestCase):
    @patch('identities.services.steam_service.requests.get')
    def test_returns_recent_games_list(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {
            'response': {'games': [{'appid': 10, 'name': 'Recent Game', 'playtime_2weeks': 120}]}
        }
        result = SteamService._fetch_recent_games('76500000000000000')
        self.assertEqual(result, [{'appid': 10, 'name': 'Recent Game', 'playtime_2weeks_minutes': 120}])

    @patch('identities.services.steam_service.requests.get')
    def test_exception_returns_empty_list(self, mock_get):
        mock_get.side_effect = Exception("network error")
        result = SteamService._fetch_recent_games('76500000000000000')
        self.assertEqual(result, [])


class FetchBadgesTests(TestCase):
    @patch('identities.services.steam_service.requests.get')
    def test_returns_badge_summary(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {
            'response': {'player_level': 12, 'player_xp': 4000, 'badges': [{'badgeid': 1, 'appid': 730, 'level': 2}]}
        }
        result = SteamService._fetch_badges('76500000000000000')
        self.assertEqual(result['player_level'], 12)
        self.assertEqual(len(result['badges']), 1)

    @patch('identities.services.steam_service.requests.get')
    def test_exception_returns_zeroed_summary(self, mock_get):
        mock_get.side_effect = Exception("network error")
        result = SteamService._fetch_badges('76500000000000000')
        self.assertEqual(result, {'player_level': 0, 'player_xp': 0, 'badges': []})


class FetchWishlistTests(TestCase):
    @patch('identities.services.steam_service.SteamService._get_app_name_lookup')
    @patch('identities.services.steam_service.requests.get')
    def test_returns_wishlist_items_with_looked_up_names(self, mock_get, mock_lookup):
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {'response': {'items': [{'appid': 730}]}}
        mock_lookup.return_value = {730: 'Counter-Strike'}

        result = SteamService._fetch_wishlist('76500000000000000')
        self.assertTrue(result['visible'])
        self.assertEqual(result['items'][0]['name'], 'Counter-Strike')
        self.assertEqual(result['items'][0]['store_url'], 'https://store.steampowered.com/app/730/')

    @patch('identities.services.steam_service.requests.get')
    def test_non_200_response_returns_not_visible(self, mock_get):
        mock_get.return_value = MagicMock(status_code=403)
        result = SteamService._fetch_wishlist('76500000000000000')
        self.assertFalse(result['visible'])
        self.assertEqual(result['items'], [])

    @patch('identities.services.steam_service.SteamService._get_app_name_lookup')
    @patch('identities.services.steam_service.requests.get')
    def test_falls_back_to_appid_label_when_name_unknown(self, mock_get, mock_lookup):
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {'response': {'items': [{'appid': 99999}]}}
        mock_lookup.return_value = {}  # name not in lookup

        result = SteamService._fetch_wishlist('76500000000000000')
        self.assertEqual(result['items'][0]['name'], 'App 99999')


class SteamServiceAppNameLookupTests(TestCase):
    """Covers _get_app_name_lookup's pagination logic directly -- FetchWishlistTests
    above mocks this method away rather than testing it, so this is the only
    coverage of the loop/last_appid chaining/no-cache-on-failure behavior."""

    def tearDown(self):
        cache.delete('steam_app_name_lookup')

    @patch('identities.services.steam_service.requests.get')
    def test_single_page_builds_lookup(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {
            'response': {
                'apps': [{'appid': 10, 'name': 'Counter-Strike'}, {'appid': 20, 'name': 'Team Fortress Classic'}],
                'have_more_results': False,
            }
        })
        lookup = SteamService._get_app_name_lookup()
        self.assertEqual(lookup[10], 'Counter-Strike')
        self.assertEqual(mock_get.call_count, 1)

    @patch('identities.services.steam_service.requests.get')
    def test_pagination_continues_until_have_more_results_false(self, mock_get):
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {
                'response': {'apps': [{'appid': 10, 'name': 'Game A'}], 'have_more_results': True, 'last_appid': 10}
            }),
            MagicMock(status_code=200, json=lambda: {
                'response': {'apps': [{'appid': 20, 'name': 'Game B'}], 'have_more_results': False}
            }),
        ]
        lookup = SteamService._get_app_name_lookup()
        self.assertEqual(lookup, {10: 'Game A', 20: 'Game B'})
        self.assertEqual(mock_get.call_count, 2)

    @patch('identities.services.steam_service.requests.get')
    def test_second_page_uses_last_appid_from_first(self, mock_get):
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {
                'response': {'apps': [], 'have_more_results': True, 'last_appid': 999}
            }),
            MagicMock(status_code=200, json=lambda: {'response': {'apps': [], 'have_more_results': False}}),
        ]
        SteamService._get_app_name_lookup()
        second_call_params = mock_get.call_args_list[1].kwargs['params']
        self.assertEqual(second_call_params['last_appid'], 999)

    @patch('identities.services.steam_service.requests.get', side_effect=Exception('network error'))
    def test_failure_returns_empty_and_does_not_cache(self, mock_get):
        lookup = SteamService._get_app_name_lookup()
        self.assertEqual(lookup, {})
        self.assertIsNone(cache.get('steam_app_name_lookup'))

    @patch('identities.services.steam_service.requests.get')
    def test_cached_lookup_skips_new_request_entirely(self, mock_get):
        cache.set('steam_app_name_lookup', {5: 'Cached Game'}, 3600)
        lookup = SteamService._get_app_name_lookup()
        self.assertEqual(lookup, {5: 'Cached Game'})
        mock_get.assert_not_called()


class FetchPlayerSummaryTests(TestCase):
    @patch('identities.services.steam_service.SteamService._fetch_wishlist')
    @patch('identities.services.steam_service.SteamService._fetch_recent_games')
    @patch('identities.services.steam_service.SteamService._fetch_owned_games')
    @patch('identities.services.steam_service.SteamService._fetch_badges')
    @patch('identities.services.steam_service.SteamService._fetch_profile_summary')
    @patch('identities.services.steam_service.requests.get')
    def test_assembles_full_profile_dict(self, mock_get, mock_summary, mock_badges, mock_owned, mock_recent, mock_wishlist):
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {
            'response': {'players': [{
                'personaname': 'TestPlayer', 'profileurl': 'https://steamcommunity.com/id/test',
                'avatar': 'a.jpg', 'avatarmedium': 'am.jpg', 'avatarfull': 'af.jpg',
                'communityvisibilitystate': 3,
            }]}
        }
        mock_summary.return_value = 'About me text'
        mock_badges.return_value = {'player_level': 1, 'player_xp': 0, 'badges': []}
        mock_owned.return_value = {'visible': True, 'count': 0, 'games': []}
        mock_recent.return_value = []
        mock_wishlist.return_value = {'visible': True, 'count': 0, 'items': []}

        result = SteamService.fetch_player_summary('76500000000000000')
        self.assertEqual(result['personaname'], 'TestPlayer')
        self.assertTrue(result['is_public'])
        self.assertEqual(result['summary'], 'About me text')

    @patch('identities.services.steam_service.requests.get')
    def test_no_players_found_raises_validation_error(self, mock_get):
        # Steam returns an empty players list for a private or nonexistent profile.
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {'response': {'players': []}}
        with self.assertRaises(ValidationError):
            SteamService.fetch_player_summary('76500000000000000')


# ---------------------------------------------------------------------------
# SteamService -- OpenID handshake logic (session/nonce), mocked network only
# ---------------------------------------------------------------------------

class VerifyCallbackTests(TestCase):
    def test_missing_nonce_in_session_raises(self):
        request = make_session_request(get_params={'nonce': 'abc', 'openid.mode': 'id_res'})
        with self.assertRaises(ValidationError):
            SteamService.verify_callback(request)

    def test_nonce_mismatch_raises(self):
        request = make_session_request(
            get_params={'nonce': 'wrong-nonce', 'openid.mode': 'id_res'},
            session_data={'steam_auth_nonce': 'correct-nonce'},
        )
        with self.assertRaises(ValidationError):
            SteamService.verify_callback(request)

    def test_wrong_openid_mode_raises(self):
        request = make_session_request(
            get_params={'nonce': 'n', 'openid.mode': 'cancel'},
            session_data={'steam_auth_nonce': 'n'},
        )
        with self.assertRaises(ValidationError):
            SteamService.verify_callback(request)

    @patch('identities.services.steam_service.requests.post')
    def test_steam_rejecting_check_authentication_raises(self, mock_post):
        mock_post.return_value = MagicMock(text='is_valid:false')
        request = make_session_request(
            get_params={
                'nonce': 'n', 'openid.mode': 'id_res',
                'openid.claimed_id': 'https://steamcommunity.com/openid/id/76500000000000000',
            },
            session_data={'steam_auth_nonce': 'n'},
        )
        with self.assertRaises(ValidationError):
            SteamService.verify_callback(request)

    @patch('identities.services.steam_service.requests.post')
    def test_valid_callback_returns_steamid64(self, mock_post):
        mock_post.return_value = MagicMock(text='is_valid:true')
        request = make_session_request(
            get_params={
                'nonce': 'n', 'openid.mode': 'id_res',
                'openid.claimed_id': 'https://steamcommunity.com/openid/id/76500000000000000',
            },
            session_data={'steam_auth_nonce': 'n'},
        )
        steamid64 = SteamService.verify_callback(request)
        self.assertEqual(steamid64, '76500000000000000')

    def test_nonce_is_single_use(self):
        # verify_callback pops the nonce from session -- a replayed callback
        # with the same query string should fail the second time.
        request = make_session_request(
            get_params={'nonce': 'n', 'openid.mode': 'cancel'},
            session_data={'steam_auth_nonce': 'n'},
        )
        with self.assertRaises(ValidationError):
            SteamService.verify_callback(request)
        self.assertNotIn('steam_auth_nonce', request.session)


# ---------------------------------------------------------------------------
# SteamService -- link / unlink / refresh
# ---------------------------------------------------------------------------

class LinkUnlinkRefreshTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='john', password='testpass123')

    @patch('identities.services.steam_service.SteamService.fetch_player_summary')
    def test_link_creates_account(self, mock_fetch):
        mock_fetch.return_value = {'personaname': 'John'}
        account = SteamService.link_steam_account(self.user, '76500000000000000')
        self.assertEqual(account.provider, 'steam')
        self.assertEqual(account.provider_uid, '76500000000000000')
        self.assertEqual(account.raw_data, {'personaname': 'John'})

    @patch('identities.services.steam_service.SteamService.fetch_player_summary')
    def test_relinking_same_user_overwrites_not_duplicates(self, mock_fetch):
        mock_fetch.return_value = {'personaname': 'John'}
        SteamService.link_steam_account(self.user, '76500000000000000')
        SteamService.link_steam_account(self.user, '76500000000000000')
        self.assertEqual(LinkedAccount.objects.filter(user=self.user, provider='steam').count(), 1)

    @patch('identities.services.steam_service.SteamService.fetch_player_summary')
    def test_cannot_link_steamid_already_claimed_by_another_user(self, mock_fetch):
        mock_fetch.return_value = {}
        other_user = User.objects.create_user(username='alice', password='testpass123')
        SteamService.link_steam_account(other_user, '76500000000000000')
        with self.assertRaises(ValidationError):
            SteamService.link_steam_account(self.user, '76500000000000000')

    @patch('identities.services.steam_service.SteamService.fetch_player_summary')
    def test_link_survives_fetch_failure_with_empty_raw_data(self, mock_fetch):
        # link_steam_account swallows exceptions from fetch_player_summary so a
        # transient Steam API failure doesn't block linking itself.
        mock_fetch.side_effect = Exception("Steam API down")
        account = SteamService.link_steam_account(self.user, '76500000000000000')
        self.assertEqual(account.raw_data, {})

    def test_unlink_removes_account(self):
        LinkedAccount.objects.create(user=self.user, provider='steam', provider_uid='765000')
        SteamService.unlink_steam_account(self.user)
        self.assertFalse(LinkedAccount.objects.filter(user=self.user, provider='steam').exists())

    def test_unlink_with_no_linked_account_does_not_raise(self):
        SteamService.unlink_steam_account(self.user)  # no-op, should not raise

    def test_refresh_with_no_linked_account_raises(self):
        with self.assertRaises(ValidationError):
            SteamService.refresh_player_data(self.user)

    @patch('identities.services.steam_service.SteamService.fetch_player_summary')
    def test_refresh_updates_raw_data(self, mock_fetch):
        LinkedAccount.objects.create(user=self.user, provider='steam', provider_uid='765000', raw_data={'personaname': 'Old'})
        mock_fetch.return_value = {'personaname': 'New'}
        account = SteamService.refresh_player_data(self.user)
        self.assertEqual(account.raw_data, {'personaname': 'New'})


# ---------------------------------------------------------------------------
# Web views -- session-authenticated, SteamService mocked at the boundary
# ---------------------------------------------------------------------------

class SteamLinkViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='john', password='testpass123')

    def test_requires_login(self):
        response = self.client.get(reverse('steam-link'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    @patch('identities.views.steam_views.SteamService.build_auth_url')
    def test_redirects_to_steam_auth_url(self, mock_build_url):
        mock_build_url.return_value = 'https://steamcommunity.com/openid/login?fake=1'
        self.client.force_login(self.user)
        response = self.client.get(reverse('steam-link'))
        self.assertRedirects(response, 'https://steamcommunity.com/openid/login?fake=1', fetch_redirect_response=False)


class SteamCallbackViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='john', password='testpass123')
        self.client.force_login(self.user)

    @patch('identities.views.steam_views.SteamService.link_steam_account')
    @patch('identities.views.steam_views.SteamService.verify_callback')
    def test_success_links_account_and_redirects_to_dashboard(self, mock_verify, mock_link):
        mock_verify.return_value = '76500000000000000'
        response = self.client.get(reverse('steam-callback'))
        self.assertRedirects(response, reverse('dashboard'))
        mock_link.assert_called_once_with(self.user, '76500000000000000')

    @patch('identities.views.steam_views.SteamService.verify_callback')
    def test_failed_verification_shows_error_message(self, mock_verify):
        mock_verify.side_effect = ValidationError("Steam login session expired or invalid. Please try again.")
        response = self.client.get(reverse('steam-callback'), follow=True)
        stored_messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('expired' in m or 'invalid' in m for m in stored_messages))


class SteamUnlinkViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='john', password='testpass123')
        self.client.force_login(self.user)
        LinkedAccount.objects.create(user=self.user, provider='steam', provider_uid='765000')

    def test_post_unlinks_account(self):
        response = self.client.post(reverse('steam-unlink'))
        self.assertRedirects(response, reverse('dashboard'))
        self.assertFalse(LinkedAccount.objects.filter(user=self.user, provider='steam').exists())

    def test_get_does_not_unlink(self):
        # steam_unlink_view only acts on request.method == 'POST' -- a GET should
        # redirect without touching the linked account.
        response = self.client.get(reverse('steam-unlink'))
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(LinkedAccount.objects.filter(user=self.user, provider='steam').exists())

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse('steam-unlink'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)


class SteamRefreshViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='john', password='testpass123')
        self.client.force_login(self.user)

    @patch('identities.views.steam_views.SteamService.refresh_player_data')
    def test_post_refreshes_and_redirects(self, mock_refresh):
        response = self.client.post(reverse('steam-refresh'))
        self.assertRedirects(response, reverse('dashboard'))
        mock_refresh.assert_called_once_with(self.user)

    @patch('identities.views.steam_views.SteamService.refresh_player_data')
    def test_no_linked_account_shows_error_not_500(self, mock_refresh):
        mock_refresh.side_effect = ValidationError("No linked Steam account to refresh.")
        response = self.client.post(reverse('steam-refresh'), follow=True)
        self.assertEqual(response.status_code, 200)
        stored_messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('No linked Steam account' in m for m in stored_messages))


class SteamProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='john', password='testpass123')
        self.client.force_login(self.user)
        self.context = Context.objects.create(owner=self.user, name='Gym')
        self.identity = IdentityProfile.objects.create(owner=self.user, context=self.context, identity_name='Gym Me')
        self.linked_account = LinkedAccount.objects.create(
            user=self.user, provider='steam', provider_uid='765000',
            raw_data={
                'personaname': 'John', 'summary': 'About me',
                'owned_games': {'visible': True, 'count': 1, 'games': [{'appid': 730, 'name': 'CS', 'playtime_forever': 10}]},
                'recent_games': [], 'badges': {'player_level': 1, 'player_xp': 0, 'badges': []},
                'wishlist': {'visible': True, 'count': 0, 'items': []},
            },
        )

    def test_get_requires_linked_account(self):
        self.linked_account.delete()
        response = self.client.get(reverse('steam-profile'))
        self.assertEqual(response.status_code, 404)

    def test_get_renders_with_identities_and_linked_account(self):
        response = self.client.get(reverse('steam-profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['linked_account'], self.linked_account)
        self.assertIn(self.identity, list(response.context['identities']))

    def test_post_materializes_selected_fields_onto_identity(self):
        response = self.client.post(reverse('steam-profile'), {
            'identity_id': self.identity.pk,
            'fields': ['owned_games', 'summary'],
        })
        self.assertRedirects(response, reverse('steam-profile'))
        self.assertTrue(IdentityAttribute.objects.filter(identity=self.identity, key='owned_games', source='steam').exists())
        self.assertTrue(IdentityAttribute.objects.filter(identity=self.identity, key='summary', source='steam').exists())

    def test_post_ignores_fields_not_in_allowlist(self):
        # e.g. a manually crafted request trying to materialize an arbitrary raw_data key.
        response = self.client.post(reverse('steam-profile'), {
            'identity_id': self.identity.pk,
            'fields': ['personaname'],  # not in STEAM_MATERIALIZE_FIELDS
        })
        self.assertRedirects(response, reverse('steam-profile'))
        self.assertFalse(IdentityAttribute.objects.filter(identity=self.identity, key='personaname').exists())

    def test_post_rejects_identity_owned_by_another_user(self):
        other_user = User.objects.create_user(username='alice', password='testpass123')
        other_context = Context.objects.create(owner=other_user, name='Alice Ctx')
        alice_identity = IdentityProfile.objects.create(owner=other_user, context=other_context, identity_name='Alice Only')

        response = self.client.post(reverse('steam-profile'), {
            'identity_id': alice_identity.pk,
            'fields': ['owned_games'],
        }, follow=True)
        self.assertFalse(IdentityAttribute.objects.filter(identity=alice_identity, key='owned_games').exists())
        stored_messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('valid identity' in m for m in stored_messages))

    def test_post_repeated_materialize_overwrites_not_duplicates(self):
        self.client.post(reverse('steam-profile'), {'identity_id': self.identity.pk, 'fields': ['summary']})
        self.client.post(reverse('steam-profile'), {'identity_id': self.identity.pk, 'fields': ['summary']})
        self.assertEqual(IdentityAttribute.objects.filter(identity=self.identity, key='summary').count(), 1)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('steam-profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)


# ---------------------------------------------------------------------------
# API views -- JWT-authenticated (force_authenticate), SteamService's real
# service-layer calls hit the DB directly here rather than being mocked, since
# ownership/validation logic in the views themselves is what's under test.
# ---------------------------------------------------------------------------

class SteamIntegrationAPITests(APITestCase):
    """Tests the API view layer (api/api_steam.py) -- request/response
    contract, ownership checks, status codes. Complements the web-view tests
    above rather than duplicating them; this hits a different set of views."""

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
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unlink_removes_account(self):
        LinkedAccount.objects.create(user=self.user, provider='steam', provider_uid='765')
        response = self.client.delete('/api/integrations/steam/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LinkedAccount.objects.filter(user=self.user).exists())


# ---------------------------------------------------------------------------
# End-to-end: a materialized Steam attribute obeys the disclosure engine
# exactly like a built-in field -- reproduces the Alice/John/Friend scenario.
# ---------------------------------------------------------------------------

class SteamDisclosureIntegrationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='john', password='testpass123')
        self.viewer = User.objects.create_user(username='alice', password='testpass123')
        self.gym_context = Context.objects.create(owner=self.owner, name='Gym')
        self.identity = IdentityProfile.objects.create(owner=self.owner, context=self.gym_context, identity_name='Gym Me')
        IdentityAttribute.objects.create(
            identity=self.identity, key='owned_games', source='steam',
            value={'visible': True, 'count': 1, 'games': [{'appid': 730, 'name': 'CS', 'playtime_forever': 10}]},
        )
        self.relationship = Relationship.objects.create(owner=self.owner, target_user=self.viewer)
        self.relationship.contexts.set([self.gym_context])

    def test_friend_sees_owned_games_when_rule_allows(self):
        DisclosureRule.objects.create(
            identity=self.identity, context=self.gym_context, field_name='owned_games', is_visible=True,
        )
        visible = DisclosureService.get_visible_identities(self.owner, self.viewer)
        self.assertEqual(len(visible), 1)
        self.assertIn('owned_games', visible[0]['visible_fields'])
        self.assertEqual(visible[0]['visible_fields']['owned_games']['games'][0]['name'], 'CS')

    def test_friend_does_not_see_owned_games_without_a_rule(self):
        # No DisclosureRule created at all for owned_games under Gym context.
        visible = DisclosureService.get_visible_identities(self.owner, self.viewer)
        self.assertEqual(visible, [])

    def test_stranger_with_no_relationship_sees_nothing(self):
        stranger = User.objects.create_user(username='bob', password='testpass123')
        DisclosureRule.objects.create(
            identity=self.identity, context=self.gym_context, field_name='owned_games', is_visible=True,
        )
        visible = DisclosureService.get_visible_identities(self.owner, stranger)
        self.assertEqual(visible, [])

    def test_owner_always_sees_own_steam_attributes_regardless_of_rules(self):
        # No DisclosureRule needed -- get_visible_identities(owner, owner) bypasses rule checks.
        visible = DisclosureService.get_visible_identities(self.owner, self.owner)
        self.assertIn('owned_games', visible[0]['visible_fields'])
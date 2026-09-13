# /identities/tests/test_github.py handles testing of the GitHub integration service and API endpoints.
from unittest.mock import patch, Mock

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from identities.models import LinkedAccount, IdentityProfile, Context, IdentityAttribute
from identities.services.github_service import GithubService, GITHUB_MATERIALIZE_FIELDS

User = get_user_model()


class GithubServiceVerifyCallbackTests(TestCase):
    """
    Tests the logic that runs *after* GitHub redirects back -- state checking
    and the token exchange. Mocks requests.post so no real call to GitHub
    happens. The actual browser redirect + consent screen is not testable
    here, same boundary as Steam's OpenID redirect.
    """

    def _build_request(self, get_params, state_in_session='abc123'):
        request = RequestFactory().get('/integrations/github/callback/', get_params, SERVER_NAME='localhost')
        request.session = {}
        if state_in_session:
            request.session['github_auth_state'] = state_in_session
        return request

    @patch('identities.services.github_service.requests.post')
    def test_valid_callback_returns_token_data(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {
            'access_token': 'gho_test123', 'refresh_token': 'ghr_test456', 'expires_in': 28800,
        })
        request = self._build_request({'state': 'abc123', 'code': 'somecode'})
        token_data = GithubService.verify_callback(request)
        self.assertEqual(token_data['access_token'], 'gho_test123')
        self.assertEqual(token_data['expires_in'], 28800)

    def test_missing_state_raises(self):
        request = self._build_request({'code': 'somecode'}, state_in_session=None)
        with self.assertRaises(ValidationError):
            GithubService.verify_callback(request)

    def test_mismatched_state_raises(self):
        request = self._build_request({'state': 'wrong', 'code': 'somecode'})
        with self.assertRaises(ValidationError):
            GithubService.verify_callback(request)

    def test_missing_code_raises(self):
        request = self._build_request({'state': 'abc123'})
        with self.assertRaises(ValidationError):
            GithubService.verify_callback(request)

    @patch('identities.services.github_service.requests.post')
    def test_missing_access_token_in_response_raises(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {'error': 'bad_verification_code'})
        request = self._build_request({'state': 'abc123', 'code': 'somecode'})
        with self.assertRaises(ValidationError):
            GithubService.verify_callback(request)


class GithubServiceFetchProfileDataTests(TestCase):
    """Tests the /user API call in isolation, mocking requests.get."""

    @patch('identities.services.github_service.requests.get')
    def test_fetch_profile_returns_expected_fields(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {
            'id': 168667777, 'login': 'Edrik-Ang', 'name': 'Edrik Ang Yi Ren',
            'avatar_url': 'https://avatars.githubusercontent.com/u/168667777',
            'html_url': 'https://github.com/Edrik-Ang',
            'bio': None, 'company': None, 'location': None,
        })
        profile = GithubService.fetch_profile_data('fake_token')
        self.assertEqual(profile['id'], 168667777)
        self.assertEqual(profile['login'], 'Edrik-Ang')
        self.assertIsNone(profile['bio'])

    @patch('identities.services.github_service.requests.get')
    def test_request_failure_raises_validation_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("connection error")
        with self.assertRaises(ValidationError):
            GithubService.fetch_profile_data('fake_token')


class GithubServiceLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.other_user = User.objects.create_user(username='bob', password='pass12345')

    @patch('identities.services.github_service.GithubService.fetch_profile_data')
    def test_link_creates_linked_account(self, mock_fetch):
        mock_fetch.return_value = {'id': 111, 'login': 'alice-gh', 'name': 'Alice'}
        token_data = {'access_token': 'gho_abc', 'refresh_token': 'ghr_abc', 'expires_in': 28800}
        account = GithubService.link_github_account(self.user, token_data)
        self.assertEqual(account.provider_uid, '111')  # requires provider_uid=str(github_id) fix in link_github_account
        self.assertEqual(account.access_token, 'gho_abc')
        self.assertEqual(account.refresh_token, 'ghr_abc')
        self.assertIsNotNone(account.token_expires_at)
        self.assertEqual(account.raw_data['login'], 'alice-gh')

    @patch('identities.services.github_service.GithubService.fetch_profile_data')
    def test_link_without_expires_in_leaves_expiry_null(self, mock_fetch):
        mock_fetch.return_value = {'id': 111, 'login': 'alice-gh'}
        token_data = {'access_token': 'gho_abc'}  # no expires_in
        account = GithubService.link_github_account(self.user, token_data)
        self.assertIsNone(account.token_expires_at)

    @patch('identities.services.github_service.GithubService.fetch_profile_data')
    def test_link_to_already_claimed_github_id_raises(self, mock_fetch):
        mock_fetch.return_value = {'id': 222, 'login': 'bob-gh'}
        LinkedAccount.objects.create(user=self.other_user, provider='github', provider_uid='222')
        with self.assertRaises(ValidationError):
            GithubService.link_github_account(self.user, {'access_token': 'gho_xyz'})

    @patch('identities.services.github_service.GithubService.fetch_profile_data')
    def test_relinking_same_user_overwrites_not_duplicates(self, mock_fetch):
        mock_fetch.side_effect = [
            {'id': 111, 'login': 'alice-gh'},
            {'id': 333, 'login': 'alice-gh-renamed'},
        ]
        GithubService.link_github_account(self.user, {'access_token': 'gho_1'})
        GithubService.link_github_account(self.user, {'access_token': 'gho_2'})
        self.assertEqual(LinkedAccount.objects.filter(user=self.user, provider='github').count(), 1)

    @patch('identities.services.github_service.GithubService.fetch_profile_data')
    def test_link_with_no_id_raises(self, mock_fetch):
        mock_fetch.return_value = {'id': None, 'login': 'ghost'}
        with self.assertRaises(ValidationError):
            GithubService.link_github_account(self.user, {'access_token': 'gho_1'})


class GithubServiceUnlinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')

    def test_unlink_removes_account(self):
        LinkedAccount.objects.create(user=self.user, provider='github', provider_uid='111')
        GithubService.unlink_github_account(self.user)
        self.assertFalse(LinkedAccount.objects.filter(user=self.user, provider='github').exists())

    def test_unlink_with_no_account_does_not_raise(self):
        GithubService.unlink_github_account(self.user)  # no-op, should not error


class GithubServiceRefreshTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')

    def test_refresh_with_no_linked_account_raises(self):
        with self.assertRaises(ValidationError):
            GithubService.refresh_github_data(self.user)

    def test_refresh_with_expired_token_raises(self):
        LinkedAccount.objects.create(
            user=self.user, provider='github', provider_uid='111',
            access_token='gho_old', token_expires_at=timezone.now() - timedelta(hours=1),
        )
        with self.assertRaises(ValidationError):
            GithubService.refresh_github_data(self.user)

    @patch('identities.services.github_service.GithubService.fetch_profile_data')
    def test_refresh_updates_raw_data(self, mock_fetch):
        mock_fetch.return_value = {'id': 111, 'login': 'alice-gh', 'bio': 'updated bio'}
        LinkedAccount.objects.create(
            user=self.user, provider='github', provider_uid='111',
            access_token='gho_current', token_expires_at=timezone.now() + timedelta(hours=1),
        )
        account = GithubService.refresh_github_data(self.user)
        self.assertEqual(account.raw_data['bio'], 'updated bio')

    @patch('identities.services.github_service.GithubService.fetch_profile_data')
    def test_refresh_with_no_expiry_set_still_works(self, mock_fetch):
        """Covers accounts linked before expiry tracking existed, or non-expiring tokens."""
        mock_fetch.return_value = {'id': 111, 'login': 'alice-gh', 'bio': 'no expiry case'}
        LinkedAccount.objects.create(
            user=self.user, provider='github', provider_uid='111',
            access_token='gho_current', token_expires_at=None,
        )
        account = GithubService.refresh_github_data(self.user)
        self.assertEqual(account.raw_data['bio'], 'no expiry case')
        

class GithubMaterializeAPIViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.other_user = User.objects.create_user(username='bob', password='pass12345')
        self.client.force_authenticate(user=self.user)
        self.context = Context.objects.create(owner=self.user, name='Work')
        self.identity = IdentityProfile.objects.create(owner=self.user, context=self.context, identity_name='Work Identity')
        self.account = LinkedAccount.objects.create(
            user=self.user, provider='github', provider_uid='111',
            raw_data={'login': 'alice-gh', 'name': 'Alice', 'bio': None, 'company': 'Acme'},
        )

    def test_materialize_creates_identity_attributes(self):
        response = self.client.post('/api/integrations/github/materialize/', {
            'identity_id': self.identity.id, 'fields': ['login', 'name', 'company'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        keys = set(IdentityAttribute.objects.filter(identity=self.identity, source='github').values_list('key', flat=True))
        self.assertEqual(keys, {'login', 'name', 'company'})

    def test_materialize_ignores_fields_outside_allowlist(self):
        response = self.client.post('/api/integrations/github/materialize/', {
            'identity_id': self.identity.id, 'fields': ['login', 'access_token'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        keys = set(IdentityAttribute.objects.filter(identity=self.identity, source='github').values_list('key', flat=True))
        self.assertEqual(keys, {'login'})  # access_token silently skipped, not in GITHUB_MATERIALIZE_FIELDS

    def test_materialize_null_field_value_stores_null(self):
        """Regression test for the NotNullViolation fixed by making IdentityAttribute.value nullable."""
        response = self.client.post('/api/integrations/github/materialize/', {
            'identity_id': self.identity.id, 'fields': ['bio'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attr = IdentityAttribute.objects.get(identity=self.identity, source='github', key='bio')
        self.assertIsNone(attr.value)

    def test_materialize_with_no_linked_account_returns_404(self):
        LinkedAccount.objects.filter(user=self.user, provider='github').delete()
        response = self.client.post('/api/integrations/github/materialize/', {
            'identity_id': self.identity.id, 'fields': ['login'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_materialize_with_other_users_identity_returns_error(self):
        other_context = Context.objects.create(owner=self.other_user, name='Other')
        other_identity = IdentityProfile.objects.create(owner=self.other_user, context=other_context, identity_name='Bob')
        response = self.client.post('/api/integrations/github/materialize/', {
            'identity_id': other_identity.id, 'fields': ['login'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GithubMaterializeFieldsAllowlistTests(TestCase):
    """Sanity check the allowlist constant itself matches what fetch_profile_data actually returns."""

    def test_allowlist_matches_scoped_fields(self):
        self.assertEqual(
            set(GITHUB_MATERIALIZE_FIELDS),
            {'login', 'name', 'avatar_url', 'html_url', 'bio', 'company', 'location'},
        )
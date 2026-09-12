## test_account_settings.py -- covers the UserProfile settings endpoint (currently just
## is_discoverable) and the matching web-facing account settings page.
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from .base import AuthenticatedAPITestCase

User = get_user_model()


class UserProfileSettingsAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('profile-settings-api')

    def test_requires_authentication(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_defaults_to_discoverable(self):
        # Signal-provisioned UserProfile defaults is_discoverable=True on creation.
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_discoverable'])

    def test_patch_turns_off_discoverability(self):
        response = self.client.patch(self.url, {'is_discoverable': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_discoverable'])
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.is_discoverable)

    def test_patch_turns_discoverability_back_on(self):
        self.user.profile.is_discoverable = False
        self.user.profile.save()

        response = self.client.patch(self.url, {'is_discoverable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_discoverable)

    def test_only_affects_own_profile(self):
        # No pk in the URL -- get_object() always returns request.user.profile,
        # so there's no way to target another user's profile through this endpoint at all.
        other_user = User.objects.create_user(username='alice', password='testpass123')
        self.client.patch(self.url, {'is_discoverable': False})

        other_user.profile.refresh_from_db()
        self.assertTrue(other_user.profile.is_discoverable)  # untouched


class AccountSettingsWebViewTests(AuthenticatedAPITestCase):
    """Uses Django's test Client (not APIClient's JWT auth) since this is a
    session-authenticated web view, not an API endpoint."""
    def setUp(self):
        super().setUp()
        self.web_client = self.client_class()
        self.web_client.force_login(self.user)
        self.url = reverse('account-settings')

    def test_requires_login(self):
        anonymous_client = self.client_class()
        response = anonymous_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)  # redirected to login

    def test_get_renders_current_setting(self):
        response = self.web_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'checked')  # default True -- checkbox should be checked

    def test_post_checked_turns_on_discoverability(self):
        self.user.profile.is_discoverable = False
        self.user.profile.save()

        response = self.web_client.post(self.url, {'is_discoverable': 'on'})
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_discoverable)

    def test_post_unchecked_turns_off_discoverability(self):
        # Unchecked checkbox is simply absent from POST data -- not sent as 'off' or False.
        response = self.web_client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.is_discoverable)
## test_auth.py -- Covers register/login and the DRF + JWT auth layer.
## covers both the web facing and api facing auth endpoints, since they share the same underlying logic and services.

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.test import TestCase
from django.urls import reverse
from identities.serializers import RegisterSerializer
from identities.services.auth_service import AuthService
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from django_rest_passwordreset.signals import post_password_reset
from django.core.cache import cache

from identities.models import Context


User = get_user_model()


class RegisterAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('api-register')

    def test_register_creates_user_and_returns_tokens(self): ## test for new user registration and token generation
        response = self.client.post(self.url, {
            'username': 'newuser',
            'email': 'newuser@example.com', 
            'password': 'testpass123',
            'password2': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED) ## should return 201 Created
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_creates_default_public_context(self): ## test for default public context creation
        self.client.post(self.url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpass123',
            'password2': 'testpass123',
        })
        user = User.objects.get(username='newuser')
        public_contexts = Context.objects.filter(owner=user, is_public_default=True)
        self.assertEqual(public_contexts.count(), 1)
        self.assertEqual(public_contexts.first().name, 'Public')

    def test_register_rejects_duplicate_username(self): ## test for duplicate username
        User.objects.create_user(username='existing', password='testpass123')
        response = self.client.post(self.url, {
            'username': 'existing',
            'email': 'other@example.com',
            'password': 'testpass123',
            'password2': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_register_rejects_missing_password(self):
        response = self.client.post(self.url, {'username': 'incomplete', 'email': 'incomplete@example.com',})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_register_rejects_missing_password2(self):
        response = self.client.post(self.url, {
            'username': 'incomplete',
            'email': 'incomplete@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password2', response.data)
    
    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(self.url, {
            'username': 'mismatcheduser',
            'email': 'mismatched@example.com',
            'password': 'testpass123',
            'password2': 'differentpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password2', response.data)
        self.assertFalse(User.objects.filter(username='mismatcheduser').exists())

    def test_register_rejects_password_under_8_chars(self):
        response = self.client.post(self.url, {
            'username': 'shortpassuser',
            'email': 'shortpass@example.com',
            'password': 'short',
            'password2': 'short'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_rejects_password_over_20_chars(self):
        response = self.client.post(self.url, {
            'username': 'longpassuser',
            'email': 'longpass@example.com',
            'password': 'Aa1' + ('a' * 21),
            'password2': 'Aa1' + ('a' * 21),
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_rejects_password_without_a_letter(self):
        response = self.client.post(self.url, {
            'username': 'alldigituser',
            'email': 'alldigit@example.com',
            'password': '12345678',
            'password2': '12345678'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_rejects_password_without_a_digit(self):
        response = self.client.post(self.url, {
            'username': 'allletteruser',
            'email': 'allletter@example.com',
            'password': 'abcdefgh',
            'password2': 'abcdefgh'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_accepts_compliant_password(self): ## Sanity check for a password that meets all requirements
        response = self.client.post(self.url, {
            'username': 'compliantuser',
            'email': 'compliant@example.com',
            'password': ' Xk4mQz9pWr2',
            'password2': ' Xk4mQz9pWr2'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_password_is_hashed_and_login_works_after(self):
        self.client.post(self.url, {
            'username': 'regressionuser',
            'email': 'regression@example.com',
            'password': 'testpass123',
            'password2': 'testpass123'
        })
        user = User.objects.get(username='regressionuser')
        self.assertTrue(user.password.startswith('pbkdf2_sha256$')) ## check that the password is hashed
        self.assertTrue(user.check_password('testpass123')) ## check that the password can be verified

        login_response = self.client.post(reverse('api-login'), {
            'username': 'regressionuser',
            'password': 'testpass123',
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(username='original', email='shared@example.com', password='testpass123')
        response = self.client.post(self.url, {
            'username': 'differentusername',
            'email': 'shared@example.com',
            'password': 'testpass123',
            'password2': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

class LoginAPITests(APITestCase):
    def setUp(self):
        self.url = reverse('api-login')
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_login_with_valid_credentials(self):
        response = self.client.post(self.url, {'username': 'testuser','password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_rejects_missing_username(self):
        response = self.client.post(self.url, {'password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_login_with_wrong_password(self):
        response = self.client.post(self.url, {'username': 'testuser','password': 'wrongpass'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) ## should return 401 Unauthorized

    def test_login_rejects_missing_password(self):
        response = self.client.post(self.url, {'username': 'testuser'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_login_with_nonexistent_user(self):
        response = self.client.post(self.url, {'username': 'nonexistent','password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) ## should return 401 Unauthorized
        self.assertIn('error', response.data)


class LogoutAPITests(APITestCase):
    def setUp(self):
        self.logout_url = reverse('api-logout')
        self.refresh_url = reverse('api-token-refresh')
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.refresh = RefreshToken.for_user(self.user)

    def test_logout_blacklists_the_token(self): ## logging out should blacklist the refresh token, preventing further use
        response = self.client.post(self.logout_url, {'refresh': str(self.refresh)})
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT) ## should return 205 Reset Content

    def test_blacklisted_token_cannot_be_used_to_refresh(self): ## blacklisted token should not be usable for refreshing access tokens
        ## test should revoke token, not just report success
        self.client.post(self.logout_url, {'refresh': str(self.refresh)})
        response = self.client.post(self.refresh_url, {'refresh': str(self.refresh)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) ## should return 401 Unauthorized

    def test_logout_without_refresh_token(self): ## logout without providing a refresh token should return 400 Bad Request
        response = self.client.post(self.logout_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 

    def test_logout_with_garbage_token(self): ## logout with an invalid token should return 400 Bad Request
        response = self.client.post(self.logout_url, {'refresh': 'definitely a real token'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 


class TokenRefreshAPITests(APITestCase):
    def setUp(self):
        self.url = reverse('api-token-refresh')
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_refresh_with_valid_token(self): ## refreshing with a valid token should return a new access token
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(self.url, {'refresh': str(refresh)})
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        self.assertIn('access', response.data)

    def test_refresh_with_garbage_token(self): ## refreshing with an invalid token should return 401 Unauthorized
        response = self.client.post(self.url, {'refresh': 'definitely a real token'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class AuthServiceUnitTests(APITestCase):
    def test_register_user_creates_public_context_directly(self):
        serializer = RegisterSerializer(data={
            'username': 'directuser', 
            'email': 'direct@gmail.com', 
            'password': 'testpass123', 
            'password2': 'testpass123',
        })
        serializer.is_valid(raise_exception=True)
        user = AuthService.register_user(serializer)
        self.assertTrue(Context.objects.filter(owner=user, is_public_default=True).exists())


class AuthenticationPermissionTests(APITestCase):

    def test_unauthenticated_user_cannot_access_contexts(self): 
        url = reverse('context-list-create-api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) 

    def test_unauthenticated_user_cannot_access_disclosure_rules(self):
        url = reverse('disclosure-rule-list-create-api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_user_cannot_search_users(self):
        url = reverse('user-search-api')  
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordResetTokenBlackListTests(APITestCase):
    """ Covers API-side path: django-rest-passwordreset's post_password_reset
    signal should blacklist all outstanding refresh token for that user."""
    def setUp(self):
        self.user = User.objects.create_user(username='resetuser', password='oldpass123')
        self.other_user = User.objects.create_user(username='otheruser', password='otherpass123')
        self.refresh1 = RefreshToken.for_user(self.user)
        self.refresh2 = RefreshToken.for_user(self.user)
        self.other_refresh = RefreshToken.for_user(self.other_user)

    def test_post_password_reset_signal_blacklists_all_user_tokens(self):
        ## simulate what django-rest-passwordreset does internally after a successful reset
        post_password_reset.send(sender=self.__class__, user=self.user)

        self.assertEqual(
            BlacklistedToken.objects.filter(token__user=self.user).count(), 2
        )

    def test_post_password_reset_signal_does_not_touch_other_users(self):
        post_password_reset.send(sender=self.__class__, user=self.user)

        self.assertEqual(
            BlacklistedToken.objects.filter(token__user=self.other_user).count(), 0
        )

    def test_blacklisted_token_after_reset_cannot_refresh(self):
        post_password_reset.send(sender=self.__class__, user=self.user)

        refresh_url = reverse('api-token-refresh')
        response = self.client.post(refresh_url, {'refresh': str(self.refresh1)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class WebPasswordResetConfirmTests(TestCase):
    """Covers the web-facing path: WebPasswordResetConfirmView.form_valid should
    blacklist all outstanding tokens once the new password is set."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='webresetuser', email='webreset@example.com', password='oldpass123'
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)


    def test_successful_web_reset_blacklists_outstanding_tokens(self):
        ## Django's PasswordResetConfirmView needs a GET first to swap the URL token
        ## for a session-stored "set-password" token -- this mirrors the real link-click flow
        confirm_url = reverse('password_reset_confirm', kwargs={'uidb64': self.uid, 'token': self.token})
        response = self.client.get(confirm_url, follow=True)
        real_confirm_url = response.redirect_chain[-1][0] if response.redirect_chain else confirm_url

        self.client.post(real_confirm_url, {
            'new_password1': 'brandnewpass456',
            'new_password2': 'brandnewpass456',
        })

        self.assertEqual(
            BlacklistedToken.objects.filter(token__user=self.user).count(), 1
        )


    def test_password_actually_changed_alongside_blacklist(self):
        confirm_url = reverse('password_reset_confirm', kwargs={'uidb64': self.uid, 'token': self.token})
        response = self.client.get(confirm_url, follow=True)
        real_confirm_url = response.redirect_chain[-1][0] if response.redirect_chain else confirm_url

        self.client.post(real_confirm_url, {
            'new_password1': 'brandnewpass456',
            'new_password2': 'brandnewpass456',
        })

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('brandnewpass456'))


class RegisterAPIRatelimitTests(APITestCase):
    def setUp(self):
        cache.clear()  ## throttle state lives in cache, not the DB -- must reset per test

    def tearDown(self):
        cache.clear()  ## avoid leaking into whatever test runs next

    def test_sixth_api_registration_attempt_in_hour_is_blocked(self):
        url = reverse('api-register')
        for i in range(5):
            response = self.client.post(url, {
                'username': f'apispam{i}',
                'email': f'apispam{i}@example.com',
                'password': 'Str0ngPassw0rd',
                'password2': 'Str0ngPassw0rd',
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"attempt {i} should succeed")

        response = self.client.post(url, {
            'username': 'apispam5',
            'email': 'apispam5@example.com',
            'password': 'Str0ngPassw0rd',
            'password2': 'Str0ngPassw0rd',
        })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
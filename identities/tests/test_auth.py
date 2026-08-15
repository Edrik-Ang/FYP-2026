## test_auth.py -- Covers register/login and the DRF + JWT auth layer.
## covers both the web facing and api facing auth endpoints, since they share the same underlying logic and services.

from django.contrib.auth import get_user_model
from django.urls import reverse
from identities.serializers import RegisterSerializer
from identities.services.auth_service import AuthService
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from identities.models import Context


User = get_user_model()


class RegisterAPITests(APITestCase):
    def setUp(self):
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

class LoginAPITests(APITestCase):
    def setUp(self):
        self.url = reverse('api-login')
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_login_with_valid_credentials(self):
        response = self.client.post(self.url, {'username': 'testuser','password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_wrong_password(self):
        response = self.client.post(self.url, {'username': 'testuser','password': 'wrongpass'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) ## should return 401 Unauthorized

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
    def test_unauthenticated_user_cannot_access_contexts(self): ## unauthenticated users should not be able to access context endpoints
        url = reverse('context-list-create-api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) ## should return 401 Unauthorized
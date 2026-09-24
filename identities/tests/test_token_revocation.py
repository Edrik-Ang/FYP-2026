"""
Test to verify the behavior of JWTs
after password change, email change and account deletion.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

User = get_user_model()


def login(client, username, password):
    r = client.post(reverse('api-login'), {'username': username, 'password': password})
    assert r.status_code == 200, r.data
    return r.data['access'], r.data['refresh']


class PasswordChangeRevocationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pw', email='pw@example.com', password='OldPass!2026x')
        self.access, self.refresh = login(self.client, 'pw', 'OldPass!2026x')

    def _change_password(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')
        r = c.patch(reverse('account-password-change-api'), {
            'current_password': 'OldPass!2026x',
            'new_password': 'NewPass!2026y', 'new_password2': 'NewPass!2026y'})
        self.assertEqual(r.status_code, 200, r.data)

    def test_T1_old_refresh_rejected_after_password_change(self):
        self._change_password()
        r = self.client.post(reverse('api-token-refresh'), {'refresh': self.refresh})
        print(f"\n[T1] refresh after password change -> {r.status_code} {r.data}")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_T2_rotated_refresh_also_revoked(self):
        # use the refresh once -> rotation issues a NEW refresh token
        r = self.client.post(reverse('api-token-refresh'), {'refresh': self.refresh})
        rotated = r.data['refresh']
        self._change_password()
        r = self.client.post(reverse('api-token-refresh'), {'refresh': rotated})
        print(f"\n[T2] rotated refresh after password change -> {r.status_code} {r.data}")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_T3_existing_access_token_still_works_after_password_change(self):
        self._change_password()
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')
        r = c.get(reverse('context-list-create-api'))
        print(f"\n[T3] OLD access token after password change -> {r.status_code}")
        # Documents behaviour: blacklisting only covers REFRESH tokens.
        self.assertEqual(r.status_code, status.HTTP_200_OK)


class EmailChangeRevocationTests(APITestCase):
    def test_T4_refresh_rejected_after_email_change(self):
        User.objects.create_user(username='em', email='em@example.com', password='OldPass!2026x')
        access, refresh = login(self.client, 'em', 'OldPass!2026x')
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        r = c.patch(reverse('account-email-change-api'),
                    {'email': 'new@example.com', 'current_password': 'OldPass!2026x'})
        self.assertEqual(r.status_code, 200, r.data)
        r = self.client.post(reverse('api-token-refresh'), {'refresh': refresh})
        print(f"\n[T4] refresh after email change -> {r.status_code} {r.data}")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class AccountDeletionTokenTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='del', password='OldPass!2026x')
        self.uid = self.user.pk
        self.access, self.refresh = login(self.client, 'del', 'OldPass!2026x')
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')
        r = c.delete(reverse('account-delete-api'), {'current_password': 'OldPass!2026x'})
        self.assertEqual(r.status_code, 204)

    def test_T5_outstanding_tokens_after_deletion(self):
        n_out = OutstandingToken.objects.filter(user__isnull=True).count()
        n_bl = BlacklistedToken.objects.filter(token__user__isnull=True).count()
        print(f"\n[T5] after deletion: OutstandingToken rows with user=NULL: {n_out}, blacklisted: {n_bl}")
        self.assertGreaterEqual(n_out, 1)   # SET_NULL: rows survive deletion, orphaned
        self.assertEqual(n_bl, n_out) 
        
    def test_T6_refresh_after_deletion(self):
        client = APIClient(raise_request_exception=False)  # behave like a real server
        r = client.post(reverse('api-token-refresh'), {'refresh': self.refresh})
        print(f"\n[T6] refresh after deletion -> {r.status_code} {r.data}")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)   # no new token issued...
        self.assertEqual(r.data['code'], 'token_not_valid')      # ...but via an unhandled DoesNotExist, not a 401

    def test_T7_access_after_deletion(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')
        r = c.get(reverse('context-list-create-api'))
        print(f"\n[T7] access token after deletion -> {r.status_code} {r.data}")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
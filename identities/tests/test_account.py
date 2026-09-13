from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from identities.models import Context, IdentityProfile, Relationship, RelationshipContext, ConnectionRequest

User = get_user_model()


class EmailChangeAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='emailuser', email='old@example.com', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.url = reverse('account-email-change-api')

    def test_change_email_success(self):
        response = self.client.patch(self.url, {'email': 'new@example.com', 'current_password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'new@example.com')

    def test_change_email_requires_correct_current_password(self):
        response = self.client.patch(self.url, {'email': 'new@example.com', 'current_password': 'wrongpass'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')

    def test_change_email_rejects_same_email(self):
        response = self.client.patch(self.url, {'email': 'old@example.com', 'current_password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_email_rejects_duplicate_email(self):
        User.objects.create_user(username='other', email='taken@example.com', password='testpass123')
        response = self.client.patch(self.url, {'email': 'taken@example.com', 'current_password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_email_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.patch(self.url, {'email': 'new@example.com', 'current_password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_email_blacklists_outstanding_tokens(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.patch(self.url, {'email': 'new@example.com', 'current_password': 'testpass123'})
        self.assertEqual(BlacklistedToken.objects.filter(token__user=self.user).count(), 1)


class PasswordChangeAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pwuser', password='oldpass123')
        self.client.force_authenticate(user=self.user)
        self.url = reverse('account-password-change-api')

    def test_change_password_success(self):
        response = self.client.patch(self.url, {
            'current_password': 'oldpass123', 'new_password': 'newpass456', 'new_password2': 'newpass456',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))

    def test_change_password_requires_correct_current_password(self):
        response = self.client.patch(self.url, {
            'current_password': 'wrongpass', 'new_password': 'newpass456', 'new_password2': 'newpass456',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_rejects_mismatched_confirmation(self):
        response = self.client.patch(self.url, {
            'current_password': 'oldpass123', 'new_password': 'newpass456', 'new_password2': 'different789',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_rejects_weak_password(self):
        response = self.client.patch(self.url, {
            'current_password': 'oldpass123', 'new_password': 'alllettersnodigits', 'new_password2': 'alllettersnodigits',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_rejects_same_as_current(self):
        response = self.client.patch(self.url, {
            'current_password': 'oldpass123', 'new_password': 'oldpass123', 'new_password2': 'oldpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.patch(self.url, {
            'current_password': 'oldpass123', 'new_password': 'newpass456', 'new_password2': 'newpass456',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_blacklists_outstanding_tokens(self):
        RefreshToken.for_user(self.user)
        self.client.patch(self.url, {
            'current_password': 'oldpass123', 'new_password': 'newpass456', 'new_password2': 'newpass456',
        })
        self.assertEqual(BlacklistedToken.objects.filter(token__user=self.user).count(), 1)


class AccountDeleteAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='deleteuser', password='testpass123')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.url = reverse('account-delete-api')

    def test_delete_account_success(self):
        response = self.client.delete(self.url, {'current_password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_delete_account_requires_correct_password(self):
        response = self.client.delete(self.url, {'current_password': 'wrongpass'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_delete_account_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.delete(self.url, {'current_password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_account_removes_owned_data(self):
        context = Context.objects.create(owner=self.user, name='Work')
        identity = IdentityProfile.objects.create(owner=self.user, context=context, identity_name='Work Me')
        self.client.delete(self.url, {'current_password': 'testpass123'})
        self.assertFalse(Context.objects.filter(pk=context.pk).exists())
        self.assertFalse(IdentityProfile.objects.filter(pk=identity.pk).exists())

    def test_delete_account_cascades_relationship_from_other_user(self):
        """Documents the accepted limitation: deleting an account also removes
        OTHER users' Relationship rows that point at it, since target_user is
        CASCADE. This is intentional per the hardening checklist decision, not
        a bug -- this test exists so a future change to that FK is a deliberate
        choice, not an accidental regression."""
        context = Context.objects.create(owner=self.other_user, name='Friends')
        ConnectionRequest.objects.create(sender=self.other_user, recipient=self.user, status=ConnectionRequest.ACCEPTED)
        relationship = Relationship.objects.create(owner=self.other_user, target_user=self.user)
        RelationshipContext.objects.create(relationship=relationship, context=context)

        self.client.delete(self.url, {'current_password': 'testpass123'})

        self.assertFalse(Relationship.objects.filter(pk=relationship.pk).exists())


class WebAccountManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='webuser', email='old@example.com', password='testpass123')
        self.client.force_login(self.user)

    def test_web_email_change_success(self):
        response = self.client.post(reverse('account-email-change'), {
            'email': 'newweb@example.com', 'current_password': 'testpass123',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newweb@example.com')
        self.assertRedirects(response, reverse('account-settings'))

    def test_web_password_change_keeps_session_valid(self):
        response = self.client.post(reverse('account-password-change'), {
            'current_password': 'testpass123', 'new_password': 'newpass456', 'new_password2': 'newpass456',
        })
        self.assertRedirects(response, reverse('account-settings'))
        # session should still be authenticated post-change, thanks to update_session_auth_hash
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)

    def test_web_account_delete_logs_out_and_removes_user(self):
        response = self.client.post(reverse('account-delete'), {'current_password': 'testpass123'})
        self.assertRedirects(response, reverse('home'))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard_response.status_code, 302)
        self.assertTrue(dashboard_response.url.startswith(reverse('login')))
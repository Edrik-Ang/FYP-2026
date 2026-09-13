# identities/tests/test_admin.py -- verifies Django admin doesn't expose encrypted OAuth tokens in plaintext.
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from identities.models import LinkedAccount

User = get_user_model()


class LinkedAccountAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='admintest', password='adminpass123', email='a@a.com')
        self.client.force_login(self.admin_user)
        self.account = LinkedAccount.objects.create(
            user=self.admin_user, provider='github', provider_uid='111',
            access_token='gho_supersecrettoken', refresh_token='ghr_supersecretrefresh',
        )

    def test_access_token_not_rendered_in_admin_change_form(self):
        url = reverse('admin:identities_linkedaccount_change', args=[self.account.pk])
        response = self.client.get(url)
        self.assertNotContains(response, 'gho_supersecrettoken')

    def test_refresh_token_not_rendered_in_admin_change_form(self):
        url = reverse('admin:identities_linkedaccount_change', args=[self.account.pk])
        response = self.client.get(url)
        self.assertNotContains(response, 'ghr_supersecretrefresh')

    def test_provider_and_uid_still_visible(self):
        # sanity check the fix didn't over-exclude -- these aren't secrets and should still show
        url = reverse('admin:identities_linkedaccount_change', args=[self.account.pk])
        response = self.client.get(url)
        self.assertContains(response, 'github')
        self.assertContains(response, '111')
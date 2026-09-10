##  identities/tests/test_method_restrictions.py
"""
Test that DRF automatic 405 behavior applies to our API Views \
proving it by request rather than assuming it from framework defaults.
Covers a range of scenarios: generic CRUD views, raw APIViews with a single custom handler, and the auth endpoints.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from identities.models import Context, IdentityProfile

User = get_user_model()


class MethodRestrictionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_authenticate(user=self.user)
        self.context = Context.objects.create(owner=self.user, name='Work')
        self.identity = IdentityProfile.objects.create(owner=self.user, context=self.context, identity_name='Work Me')

    ## generic ListCreateAPIView -- should reject PUT/PATCH/DELETE at the collection level
    def test_context_list_rejects_delete(self):
        response = self.client.delete(reverse('context-list-create-api'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_context_list_rejects_patch(self):
        response = self.client.patch(reverse('context-list-create-api'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ## generic RetrieveUpdateDestroyAPIView -- should reject POST at the detail level
    def test_context_detail_rejects_post(self):
        url = reverse('context-retrieve-update-destroy-api', kwargs={'pk': self.context.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ## raw APIView, single custom .post() handler -- should reject GET/DELETE entirely
    def test_login_rejects_get(self):
        response = self.client.get(reverse('api-login'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_register_rejects_get(self):
        response = self.client.get(reverse('api-register'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_logout_rejects_get(self):
        response = self.client.get(reverse('api-logout'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ## raw APIView with only .get() and .delete() -- should reject POST/PATCH/PUT
    def test_steam_linked_account_rejects_post(self):
        response = self.client.post(reverse('steam-linked-account-api'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ## materialize is post-only -- should reject GET
    def test_steam_materialize_rejects_get(self):
        response = self.client.get(reverse('steam-materialize-api'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_github_materialize_rejects_get(self):
        response = self.client.get(reverse('github-materialize-api'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ## read-only ListAPIView -- should reject POST
    def test_user_search_rejects_post(self):
        response = self.client.post(reverse('user-search-api'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    ## GET-only ProfileAPIView -- should reject POST
    def test_profile_rejects_post(self):
        url = reverse('profile-api', kwargs={'username': self.user.username})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
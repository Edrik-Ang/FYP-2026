## test_context.py covers Context CRUF and ContextService's business rules: 
# duplicate-name rejection (scoped by user), blocking rename/delete of the public default context, and blocking delete while still assigned to identity.

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from identities.models import Context, IdentityProfile
from .base import AuthenticatedAPITestCase


User = get_user_model()


class ContextListCreateAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('context-list-create-api')

    def test_list_contexts_returns_only_own(self): ## should return own contexts, not other users' contexts
        Context.objects.create(owner=self.user, name='Work')
        other_user = User.objects.create_user(username='alice', password='testpass123')
        Context.objects.create(owner=other_user, name='Alice Only')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        name = [c['name'] for c in response.data]
        self.assertIn('Work', name) 
        self.assertNotIn('Alice Only', name)

    def test_create_context(self): ## should create a new context for the authenticated user
        response = self.client.post(self.url, {'name': 'Work'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED) ## should return 201 Created
        self.assertTrue(Context.objects.filter(owner=self.user, name='Work').exists())

    def test_create_context_rejects_duplicate_name(self): ## should reject duplicate context names for the same user
        Context.objects.create(owner=self.user, name='Work')
        response = self.client.post(self.url, {'name': 'Work'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_same_name_allowed_for_different_owners(self): ## should allow same context name for different users
        other_user = User.objects.create_user(username='alice', password='testpass123')
        Context.objects.create(owner=other_user, name='Work')
        response = self.client.post(self.url, {'name': 'Work'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED) ## should return 201 Created

class ContextDetailAPITest(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.context = Context.objects.create(owner=self.user, name='Work')
        self.context2 = Context.objects.create(owner=self.user, name='Personal')
        self.url = reverse('context-retrieve-update-destroy-api', kwargs={'pk': self.context.pk})

    def test_retrieve_context(self): ## should retrieve the context details
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        self.assertEqual(response.data['name'], 'Work')

    def test_update_context(self): ## should update the context name
        response = self.client.patch(self.url, {'name': 'Colleagues'})
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        self.context.refresh_from_db()
        self.assertEqual(self.context.name, 'Colleagues')

    def test_delete_context(self): ## should delete the context
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT) ## should return 204 No Content
        self.assertFalse(Context.objects.filter(pk=self.context.pk).exists())

    def test_cannot_delete_context_with_identities(self): ## should not allow deletion of context if it has associated identities
        IdentityProfile.objects.create(owner=self.user, context=self.context, identity_name='Work Identity')
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_cannot_rename_public_context(self):
        public_context = Context.objects.create(owner=self.user, name='Public', is_public_default=True)
        url = reverse('context-retrieve-update-destroy-api', kwargs={'pk': public_context.pk})
        response = self.client.patch(url, {'name': 'New Public Name'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_cannot_delete_public_context(self):
        public_context = Context.objects.create(owner=self.user, name='Public', is_public_default=True)
        url = reverse('context-retrieve-update-destroy-api', kwargs={'pk': public_context.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request
        self.assertTrue(Context.objects.filter(pk=public_context.pk).exists())

    def test_cannot_edit_another_users_context(self):
        other_user = User.objects.create_user(username='alice', password='testpass123')
        other_context = Context.objects.create(owner=other_user, name='Alice Work')
        url = reverse('context-retrieve-update-destroy-api', kwargs={'pk': other_context.pk})
        response = self.client.patch(url, {'name': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) ## should return 404 Not Found

    def test_cannot_delete_another_users_context(self):
        other_user = User.objects.create_user(username='alice', password='testpass123')
        other_context = Context.objects.create(owner=other_user, name='Alice Work')
        url = reverse('context-retrieve-update-destroy-api', kwargs={'pk': other_context.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) ## should return 404 Not Found
        self.assertTrue(Context.objects.filter(pk=other_context.pk).exists())
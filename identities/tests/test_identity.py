## test_identity.py -- Covers identity CRUD and identityProfileSerializer's business rules:
## cross-owner context assignment rejection, duplicate identity name blocked per context (allowed across different contexts),
## ownership enforcement via queryset filtering on retrieve/update/delete.
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from identities.models import Context, IdentityProfile
from .base import AuthenticatedAPITestCase

User = get_user_model()


class IdentityListCreateAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.context = Context.objects.create(owner=self.user, name='Work')
        self.url = reverse('identity-list-create-api')

    def test_list_identities_returns_only_own(self): ## should return only own identities, not other users' identities
        IdentityProfile.objects.create(owner=self.user, context=self.context, identity_name='Work Me')
        other_user = User.objects.create_user(username='alice', password='testpass123')
        other_context = Context.objects.create(owner=other_user, name='Alice Work')
        IdentityProfile.objects.create(owner=other_user, context=other_context, identity_name='Alice Only')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        names = [i['identity_name'] for i in response.data]
        self.assertIn('Work Me', names)
        self.assertNotIn('Alice Only', names) ## should not return other user's identity

    def test_create_identity(self): ## should create new identity under owned context
        response = self.client.post(self.url, {
            'identity_name': 'Work Me', 'description': 'Backend developer', 'context':self.context.pk,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED) ## should return 201 Created
        self.assertTrue(IdentityProfile.objects.filter(owner=self.user, identity_name='Work Me').exists())

    def test_create_identity_with_someone_elses_context(self): ## should reject assigning identity to another user's context
        other_user = User.objects.create_user(username='alice', password='testpass123')
        other_context = Context.objects.create(owner=other_user, name='Alice Work')
        response = self.client.post(self.url, {
            'identity_name': 'Sneaky', 'context':other_context.pk,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_create_identity_rejects_duplicate_name_in_same_context(self): ## should reject duplicate identity name in same context
        IdentityProfile.objects.create(owner=self.user, context=self.context, identity_name='Work Me')
        response = self.client.post(self.url, {
            'identity_name': 'Work Me', 'context':self.context.pk,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_same_name_allowed_in_different_context(self): ## uniqueness is scope per-context, not global
        IdentityProfile.objects.create(owner=self.user, context=self.context, identity_name='Me')
        personal_context = Context.objects.create(owner=self.user, name='Personal')
        response = self.client.post(self.url, {'identity_name':'Me', 'context':personal_context.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED) ## should return 201 Created


class IdentityDetailAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.context = Context.objects.create(owner=self.user, name='Work')
        self.other_context = Context.objects.create(owner=self.user, name='Personal')
        self.identity = IdentityProfile.objects.create(owner=self.user, context=self.context, identity_name='Work Me', description='Backend developer')
        self.url = reverse('identity-retrieve-update-destroy-api', kwargs={'pk': self.identity.pk})

    def test_retrieve_identity(self): ## should retrieve own identity
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        self.assertEqual(response.data['identity_name'], 'Work Me')

    def test_update_identity(self): ## should update own identity
        response = self.client.patch(self.url, {'description': 'Updated bio.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        self.identity.refresh_from_db()
        self.assertEqual(self.identity.description, 'Updated bio.')

    def test_move_identity_to_another_owned_context(self): ## should allow moving identity to another context owned by same user
        response = self.client.patch(self.url, {'context': self.other_context.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        self.identity.refresh_from_db()
        self.assertEqual(self.identity.context_id, self.other_context.pk)

    def test_move_identity_to_another_users_context(self): ## should reject moving identity to another user's context
        other_user = User.objects.create_user(username='alice', password='testpass123')
        other_context = Context.objects.create(owner=other_user, name='Alice Work')
        response = self.client.patch(self.url, {'context': other_context.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_delete_identity(self): ## should delete own identity
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT) ## should return 204 No Content
        self.assertFalse(IdentityProfile.objects.filter(pk=self.identity.pk).exists())

    def test_cannot_retrieve_another_users_identity(self): ## should 404, not leak existence of another user's identity
        other_user = User.objects.create_user(username='alice', password='testpass123')
        other_context = Context.objects.create(owner=other_user, name='Alice Work')
        other_identity = IdentityProfile.objects.create(owner=other_user, context=other_context, identity_name='Alice Only')
        other_url = reverse('identity-retrieve-update-destroy-api', kwargs={'pk': other_identity.pk})
        response = self.client.get(other_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) ## should return 404 Not Found

    def test_cannot_edit_another_users_identity(self): ## same ownership protection applies to update
        other_user = User.objects.create_user(username='alice', password='testpass123')
        other_context = Context.objects.create(owner=other_user, name='Alice Work')
        other_identity = IdentityProfile.objects.create(owner=other_user, context=other_context, identity_name='Alice Only')
        other_url = reverse('identity-retrieve-update-destroy-api', kwargs={'pk': other_identity.pk})
        response = self.client.patch(other_url, {'description': 'Hacked!'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) ## should return 404 Not Found
    
# TODO:
# list identities --> 200
# create identity --> 201
# create with someone else's context --> 400
# update identity --> 200
# move identity to another owned context --> 200
# move identity to another user's context --> 400
# delete identity --> 204
# retrieve another user's identity --> 404
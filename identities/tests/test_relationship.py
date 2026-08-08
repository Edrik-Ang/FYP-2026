## test_relationship.py -- covers testing for Relationship CRUF and RelationshipSerializer's business rules:
## Context-tag ownership, no self-referential relationships, 
## at least one context required, no duplicate owner/target_user pairs, and public excluded as a tag context. (see disclosure)
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from identities.models import Context, Relationship
from .base import AuthenticatedAPITestCase

User = get_user_model()


class RelationshipListCreateAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.context = Context.objects.create(owner=self.user, name='Friend')
        self.other_user = User.objects.create_user(username='alice', password='testpass123')
        self.url = reverse('relationship-list-create-api')

    def test_list_relationships_returns_only_own(self): ## should return only own relationships, not other user's relationships
        relationship = Relationship.objects.create(owner=self.user, target_user=self.other_user)
        relationship.contexts.add(self.context)
        bob = User.objects.create_user(username='bob', password='testpass123')
        bob_context = Context.objects.create(owner=bob, name='Colleague')
        their_relationship = Relationship.objects.create(owner=bob, target_user=self.other_user)
        their_relationship.contexts.add(bob_context)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        target_usernames = [r['target_username'] for r in response.data]
        self.assertEqual(target_usernames, ['alice']) ## should return only own relationship to alice

    def test_create_relationship(self): ## should create new relationship with at least one context
        response = self.client.post(self.url, {'target_user': self.other_user.pk, 'contexts': [self.context.pk],})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED) ## should return 201 Created
        self.assertTrue(Relationship.objects.filter(owner=self.user, target_user=self.other_user).exists())

    def test_cannot_relate_to_yourself(self): ## should reject self-referential relationship
        response = self.client.post(self.url, {'target_user': self.user.pk, 'contexts': [self.context.pk],})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_create_relationship_with_someone_elses_context(self): ## should reject using another user's context
        alice_context = Context.objects.create(owner=self.other_user, name='Alice Context')
        response = self.client.post(self.url, {'target_user': self.other_user.pk, 'contexts': [alice_context.pk],})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_create_relationship_requires_at_least_one_context(self): ## should reject empty context list
        response = self.client.post(self.url, {'target_user': self.other_user.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_cannot_use_public_context_as_tag(self): ## public is auto-granted, not taggable.
        public_context = Context.objects.create(owner=self.user, name='Public', is_public_default=True)
        response = self.client.post(self.url, {'target_user': self.other_user.pk, 'contexts': [public_context.pk],})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request

    def test_cannot_create_duplicate_relationship(self):
        existing_relationship = Relationship.objects.create(owner=self.user, target_user=self.other_user)
        existing_relationship.contexts.set([self.context])
        response = self.client.post(self.url, {'target_user': self.other_user.pk, 'contexts': [self.context.pk],})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) ## should return 400 Bad Request


class RelationshipDetailAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.context = Context.objects.create(owner=self.user, name='Friend')
        self.other_context = Context.objects.create(owner=self.user, name='Colleague')
        self.other_user = User.objects.create_user(username='alice', password='testpass123')

        self.relationship = Relationship.objects.create(owner=self.user, target_user=self.other_user)
        self.relationship.contexts.set([self.context])
        self.url = reverse('relationship-retrieve-update-destroy-api', kwargs={'pk': self.relationship.pk})

    def test_retrieve_relationship(self): ## should retrieve own relationship
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        self.assertEqual(response.data['target_username'], 'alice') 

    def test_update_contexts(self): ## should replace the tagged contexts
        response = self.client.patch(self.url, {'contexts': [self.other_context.pk]})
        self.assertEqual(response.status_code, status.HTTP_200_OK) ## should return 200 OK
        self.relationship.refresh_from_db()
        tagged_names = list(self.relationship.contexts.values_list('name', flat=True))
        self.assertEqual(tagged_names, ['Colleague']) ## should have only the updated context

    def test_delete_relationship(self): ## should delete own relationship
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT) ## should return 204 No Content
        self.assertFalse(Relationship.objects.filter(pk=self.relationship.pk).exists())

    def test_cannot_retrieve_another_users_relationship(self): ## should reject retrieval of another user's relationship
        bob = User.objects.create_user(username='bob', password='testpass123')
        alice_context = Context.objects.create(owner=self.other_user, name='Alice Context')
        alice_relationship = Relationship.objects.create(owner=self.other_user, target_user=bob)
        alice_relationship.contexts.set([alice_context])

        url = reverse('relationship-retrieve-update-destroy-api', kwargs={'pk': alice_relationship.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) ## should return 404 Not Found

    def test_cannot_edit_another_users_relationship(self): ## should reject editing of another user's relationship
        bob = User.objects.create_user(username='bob', password='testpass123')
        alice_context = Context.objects.create(owner=self.other_user, name='Alice Context')
        alice_relationship = Relationship.objects.create(owner=self.other_user, target_user=bob)
        alice_relationship.contexts.set([alice_context])
        url = reverse('relationship-retrieve-update-destroy-api', kwargs={'pk': alice_relationship.pk})
        response = self.client.patch(url, {'contexts': [self.context.pk]})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) ## should return 404 Not Found

    def test_cannot_delete_another_users_relationship(self): ## should reject deletion of another user's relationship
        bob = User.objects.create_user(username='bob', password='testpass123')
        alice_context = Context.objects.create(owner=self.other_user, name='Alice Context')
        alice_relationship = Relationship.objects.create(owner=self.other_user, target_user=bob)
        alice_relationship.contexts.set([alice_context])

        url = reverse('relationship-retrieve-update-destroy-api', kwargs={'pk': alice_relationship.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) ## should return 404 Not Found
        self.assertTrue(Relationship.objects.filter(pk=alice_relationship.pk).exists()) ## should still exist

# TODO:
# list relationships --> 200
# create relationship --> 201
# cannot relate to yourself --> 400
# cannot use another user's context --> 400
# cannot create duplicate relationship --> 400
# must have at least 1 context --> 400
# update contexts --> 200
# delete relationship --> 204
# cannot view another user's relationship --> 404
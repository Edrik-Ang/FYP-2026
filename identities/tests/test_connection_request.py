## /identities/tests/test_connection_request.py -- covers RelationshipService.create_request()'s business rules:
## the is_discoverable gate (and its generic-error indistinguishability from a nonexistent
## user), duplicate-pending rejection, self-request rejection, already-connected rejection,
## and the resend cooldown after a decline. Service-level tests, not API-level -- no view/URL
## exists yet for sending a connection request.
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ..tests.base import AuthenticatedAPITestCase
from identities.models import ConnectionRequest
from identities.services.relationship_service import RelationshipService

User = get_user_model()


class CreateConnectionRequestTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username='alice', password='testpass123')
        self.bob = User.objects.create_user(username='bob', password='testpass123')
        # UserProfile is auto-provisioned by the post_save signal on User creation

    def test_create_request_success(self):
        req = RelationshipService.create_request(self.alice, 'bob')
        self.assertEqual(req.sender, self.alice)
        self.assertEqual(req.recipient, self.bob)
        self.assertEqual(req.status, ConnectionRequest.PENDING)

    def test_rejects_duplicate_pending_request(self):
        RelationshipService.create_request(self.alice, 'bob')
        with self.assertRaises(ValidationError):
            RelationshipService.create_request(self.alice, 'bob')

    def test_rejects_self_request(self):
        with self.assertRaises(ValidationError):
            RelationshipService.create_request(self.alice, 'alice')

    def test_nonexistent_user_and_undiscoverable_user_give_identical_error(self):
        # modes must be indistinguishable to the caller.
        self.bob.profile.is_discoverable = False
        self.bob.profile.save()

        with self.assertRaises(ValidationError) as undiscoverable_ctx:
            RelationshipService.create_request(self.alice, 'bob')

        with self.assertRaises(ValidationError) as nonexistent_ctx:
            RelationshipService.create_request(self.alice, 'nonexistent_user')

        self.assertEqual(
            str(undiscoverable_ctx.exception.detail[0]),
            str(nonexistent_ctx.exception.detail[0]),
        )

    def test_undiscoverable_user_blocks_request_synchronously_nothing_persisted(self):
        self.bob.profile.is_discoverable = False
        self.bob.profile.save()

        with self.assertRaises(ValidationError):
            RelationshipService.create_request(self.alice, 'bob')

        self.assertFalse(
            ConnectionRequest.objects.filter(sender=self.alice, recipient=self.bob).exists()
        )

    def test_rejects_request_to_already_connected_user(self):
        req = RelationshipService.create_request(self.alice, 'bob')
        req.status = ConnectionRequest.ACCEPTED
        req.responded_at = timezone.now()
        req.save()

        with self.assertRaises(ValidationError):
            RelationshipService.create_request(self.alice, 'bob')

    def test_cooldown_blocks_resend_shortly_after_decline(self):
        req = RelationshipService.create_request(self.alice, 'bob')
        req.status = ConnectionRequest.DECLINED
        req.responded_at = timezone.now()
        req.save()

        with self.assertRaises(ValidationError):
            RelationshipService.create_request(self.alice, 'bob')

    def test_resend_allowed_once_cooldown_expires(self):
        req = RelationshipService.create_request(self.alice, 'bob')
        req.status = ConnectionRequest.DECLINED
        req.responded_at = timezone.now() - timedelta(hours=2)  # cooldown is 1 hour
        req.save()

        new_req = RelationshipService.create_request(self.alice, 'bob')
        self.assertEqual(new_req.status, ConnectionRequest.PENDING)

    def test_reverse_direction_is_independent(self): # A->B and B->A are separate, unrestricted rows.
        RelationshipService.create_request(self.alice, 'bob')
        reverse_req = RelationshipService.create_request(self.bob, 'alice')
        self.assertEqual(reverse_req.sender, self.bob)
        self.assertEqual(reverse_req.recipient, self.alice)

    def test_existing_relationships_unaffected_by_is_discoverable_toggle(self):
        # Locked decision: is_discoverable only gates NEW requests. An
        # existing Relationship (tagged before or regardless of the toggle)
        # is untouched -- it's governed entirely by RelationshipContext,
        # a separate path this method never touches.
        from identities.models import Context, Relationship

        context = Context.objects.create(owner=self.alice, name='Friend')
        relationship = Relationship.objects.create(owner=self.alice, target_user=self.bob)
        relationship.contexts.set([context])

        self.bob.profile.is_discoverable = False
        self.bob.profile.save()

        # The existing Relationship still exists and is untouched
        self.assertTrue(
            Relationship.objects.filter(owner=self.alice, target_user=self.bob).exists()
        )
        self.assertIn(context, relationship.contexts.all())


class RespondToConnetionRequestTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username='alice', password='testpass123')
        self.bob = User.objects.create_user(username='bob', password='testpass123')

    def test_accept_request_success(self):
        req = RelationshipService.create_request(self.alice, 'bob')
        accepted = RelationshipService.accept_request(req, self.bob)
        self.assertEqual(accepted.status, ConnectionRequest.ACCEPTED)
        self.assertIsNotNone(accepted.responded_at)

    def test_decline_request_success(self):
        req = RelationshipService.create_request(self.alice, 'bob')
        declined = RelationshipService.decline_request(req, self.bob)
        self.assertEqual(declined.status, ConnectionRequest.DECLINED)
        self.assertIsNotNone(declined.responded_at)

    def test_cannot_accept_already_responded_request(self):
        req = RelationshipService.create_request(self.alice, 'bob')
        RelationshipService.accept_request(req, self.bob)
        with self.assertRaises(ValidationError):
            RelationshipService.accept_request(req, self.bob)

    def test_cannot_decline_already_responded_request(self):
        req = RelationshipService.create_request(self.alice, 'bob')
        RelationshipService.decline_request(req, self.bob)
        with self.assertRaises(ValidationError):
            RelationshipService.decline_request(req, self.bob)

    def test_sender_cannot_accept_own_sent_request(self):
        # Only the recipient can respond -- the sender attempting to
        # accept/decline their own outgoing request must be rejected.
        req = RelationshipService.create_request(self.alice, 'bob')
        with self.assertRaises(ValidationError):
            RelationshipService.accept_request(req, self.alice)

    def test_sender_cannot_decline_own_sent_request(self):
        req = RelationshipService.create_request(self.alice, 'bob')
        with self.assertRaises(ValidationError):
            RelationshipService.decline_request(req, self.alice)

    def test_unrelated_user_cannot_respond(self):
        charlie = User.objects.create_user(username='charlie', password='testpass123')
        req = RelationshipService.create_request(self.alice, 'bob')
        with self.assertRaises(ValidationError):
            RelationshipService.accept_request(req, charlie)

    def test_accepting_does_not_create_a_relationship(self):
        # accepting a ConnectionRequest never touches, because the RelationshipService is only responsible for the request itself.
        from identities.models import Relationship

        req = RelationshipService.create_request(self.alice, 'bob')
        RelationshipService.accept_request(req, self.bob)

        self.assertFalse(
            Relationship.objects.filter(owner=self.alice, target_user=self.bob).exists()
        )
        self.assertFalse(
            Relationship.objects.filter(owner=self.bob, target_user=self.alice).exists()
        )

    def test_decline_starts_cooldown_for_resend(self):
        # Integration check: decline_request() sets responded_at, and
        # create_request()'s cooldown check reads exactly that field.
        req = RelationshipService.create_request(self.alice, 'bob')
        RelationshipService.decline_request(req, self.bob)

        with self.assertRaises(ValidationError):
            RelationshipService.create_request(self.alice, 'bob')

class ConnectionRequestCreateAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.bob = User.objects.create_user(username='bob', password='testpass123')
        self.url = reverse('connection-request-create-api')

    def test_requires_authentication(self):
        self.client.credentials()  # clear the auth header set in base setUp
        response = self.client.post(self.url, {'recipient_username': 'bob'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_request_success(self):
        response = self.client.post(self.url, {'recipient_username': 'bob'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['recipient_username'], 'bob')

    def test_nonexistent_and_undiscoverable_user_give_identical_response(self):
        self.bob.profile.is_discoverable = False
        self.bob.profile.save()

        undiscoverable_response = self.client.post(self.url, {'recipient_username': 'bob'})
        nonexistent_response = self.client.post(self.url, {'recipient_username': 'nonexistent_user'})

        self.assertEqual(undiscoverable_response.status_code, nonexistent_response.status_code)
        self.assertEqual(undiscoverable_response.data, nonexistent_response.data)

    def test_missing_recipient_username_is_bad_request(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ConnectionRequestListAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.bob = User.objects.create_user(username='bob', password='testpass123')
        self.charlie = User.objects.create_user(username='charlie', password='testpass123')
        self.incoming_url = reverse('connection-request-incoming-api')
        self.outgoing_url = reverse('connection-request-outgoing-api')

    def test_incoming_shows_only_pending_requests_sent_to_you(self):
        ConnectionRequest.objects.create(sender=self.bob, recipient=self.user)
        ConnectionRequest.objects.create(sender=self.charlie, recipient=self.bob)  # not involving self.user

        response = self.client.get(self.incoming_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['sender_username'], 'bob')

    def test_incoming_excludes_already_responded_requests(self):
        req = ConnectionRequest.objects.create(sender=self.bob, recipient=self.user)
        req.status = ConnectionRequest.ACCEPTED
        req.save()

        response = self.client.get(self.incoming_url)
        self.assertEqual(response.data, [])

    def test_outgoing_shows_all_statuses_of_requests_you_sent(self):
        pending = ConnectionRequest.objects.create(sender=self.user, recipient=self.bob)
        declined = ConnectionRequest.objects.create(sender=self.user, recipient=self.charlie)
        declined.status = ConnectionRequest.DECLINED
        declined.save()

        response = self.client.get(self.outgoing_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = {r['status'] for r in response.data}
        self.assertEqual(statuses, {'pending', 'declined'})

    def test_outgoing_does_not_show_requests_sent_to_you(self):
        ConnectionRequest.objects.create(sender=self.bob, recipient=self.user)
        response = self.client.get(self.outgoing_url)
        self.assertEqual(response.data, [])


class ConnectionRequestAcceptDeclineAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.bob = User.objects.create_user(username='bob', password='testpass123')
        self.charlie = User.objects.create_user(username='charlie', password='testpass123')
        self.request_to_user = ConnectionRequest.objects.create(sender=self.bob, recipient=self.user)
        self.accept_url = reverse('connection-request-accept-api', kwargs={'pk': self.request_to_user.pk})
        self.decline_url = reverse('connection-request-decline-api', kwargs={'pk': self.request_to_user.pk})

    def test_recipient_can_accept(self):
        response = self.client.post(self.accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'accepted')

    def test_recipient_can_decline(self):
        response = self.client.post(self.decline_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'declined')

    def test_sender_cannot_accept_their_own_sent_request(self):
        # self.user is the recipient here; switch to Bob (the sender) and confirm 404,
        # not 403 -- same non-leaking pattern as Relationship/Context detail views.
        self.authenticate_as(self.bob)
        response = self.client.post(self.accept_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unrelated_user_cannot_accept(self):
        self.authenticate_as(self.charlie)
        response = self.client.post(self.accept_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_accept_already_responded_request(self):
        self.client.post(self.accept_url)
        response = self.client.post(self.accept_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_requires_authentication(self):
        self.client.credentials()
        response = self.client.post(self.accept_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
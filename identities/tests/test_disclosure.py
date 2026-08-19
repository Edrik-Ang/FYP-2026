## test_disclosure.py -- covers DisclosureRule CRUF 
# plus the disclosure Engine itself: deny-by-default with no relationship,
# the auto-granted public context, per-field gating, and the union rule for multiple contexts.
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from identities.models import Context, IdentityProfile, DisclosureRule, Relationship
from .base import AuthenticatedAPITestCase

User = get_user_model()

class DisclosureRuleListCreateAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.work_context = Context.objects.create(owner=self.user, name="Work")
        self.colleague_context = Context.objects.create(owner=self.user, name="Colleague")
        self.identity = IdentityProfile.objects.create(owner=self.user, context=self.work_context, identity_name='Work Me',)
        self.url = reverse('disclosure-rule-list-create-api')

    def test_list_own_rules_returns_only_own(self): ## should return own rules, not other users
        DisclosureRule.objects.create(
            identity=self.identity, context=self.colleague_context,
            field_name='identity_name',is_visible=True,
        )
        other_user = User.objects.create_user(username='alice', password='testpass123')
        alice_work = Context.objects.create(owner=other_user, name='Alice Work')
        alice_ctx = Context.objects.create(owner=other_user, name='Alice Ctx')
        alice_identity = IdentityProfile.objects.create(owner=other_user, context=alice_work, identity_name='Alice Only')
        DisclosureRule.objects.create(
            identity=alice_identity, context=alice_ctx, field_name='identity_name', is_visible=True,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)  ## should return 200 OK
        identity_ids = [r['identity'] for r in response.data]
        self.assertIn(self.identity.pk, identity_ids)
        self.assertNotIn(alice_identity.pk, identity_ids)

    def test_create_rule(self):  ## should create a rule for an owned identity + context
        response = self.client.post(self.url, {
            'identity': self.identity.pk, 'context': self.colleague_context.pk,
            'field_name': 'identity_name', 'is_visible': True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  ## should return 201 Created
        self.assertTrue(DisclosureRule.objects.filter(
            identity=self.identity, context=self.colleague_context, field_name='identity_name',
        ).exists())

    def test_create_rule_with_someone_elses_identity(self):  ## should reject an identity you don't own
        other_user = User.objects.create_user(username='alice', password='testpass123')
        alice_ctx = Context.objects.create(owner=other_user, name='Alice Work')
        alice_identity = IdentityProfile.objects.create(owner=other_user, context=alice_ctx, identity_name='Alice Only')

        response = self.client.post(self.url, {
            'identity': alice_identity.pk, 'context': self.colleague_context.pk,
            'field_name': 'identity_name', 'is_visible': True,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  ## should return 400 Bad Request

    def test_create_rule_with_someone_elses_context(self):  ## should reject a context you don't own
        other_user = User.objects.create_user(username='alice', password='testpass123')
        alice_ctx = Context.objects.create(owner=other_user, name='Alice Ctx')

        response = self.client.post(self.url, {
            'identity': self.identity.pk, 'context': alice_ctx.pk,
            'field_name': 'identity_name', 'is_visible': True,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  ## should return 400 Bad Request

    def test_create_rule_rejects_invalid_field_name(self):  ## field_name must be a real field or attribute key
        response = self.client.post(self.url, {
            'identity': self.identity.pk, 'context': self.colleague_context.pk,
            'field_name': 'ssn', 'is_visible': True,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  ## should return 400 Bad Request

    def test_can_use_public_context(self):
        # NOTE: reversed from the original plan's "cannot use public context
        # --> 400". That restriction was removed earlier -- Public HAS to be
        # a valid disclosure-rule context, since a public-facing identity
        # (rules keyed on the Public context) is literally how the public
        # profile feature works. Blocking it here would silently disable that.
        public_context = Context.objects.create(owner=self.user, name='Public', is_public_default=True)
        response = self.client.post(self.url, {
            'identity': self.identity.pk, 'context': public_context.pk,
            'field_name': 'identity_name', 'is_visible': True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  ## should return 201 Created


class DisclosureRuleDetailAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.work_context = Context.objects.create(owner=self.user, name='Work')
        self.colleague_context = Context.objects.create(owner=self.user, name='Colleague')
        self.identity = IdentityProfile.objects.create(
            owner=self.user, context=self.work_context, identity_name='Work Me',
        )
        self.rule = DisclosureRule.objects.create(
            identity=self.identity, context=self.colleague_context,
            field_name='identity_name', is_visible=False,
        )
        self.url = reverse('disclosure-rule-retrieve-update-destroy-api', kwargs={'pk': self.rule.pk})

    def test_retrieve_rule(self):  ## should retrieve the rule details
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)  ## should return 200 OK
        self.assertEqual(response.data['field_name'], 'identity_name')

    def test_update_visibility(self):  ## should toggle is_visible
        response = self.client.patch(self.url, {'is_visible': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)  ## should return 200 OK
        self.rule.refresh_from_db()
        self.assertTrue(self.rule.is_visible)

    def test_delete_rule(self):  ## should delete the rule
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)  ## should return 204 No Content
        self.assertFalse(DisclosureRule.objects.filter(pk=self.rule.pk).exists())

    def test_cannot_retrieve_another_users_rule(self):  ## should 404, not leak that it exists
        other_user = User.objects.create_user(username='alice', password='testpass123')
        alice_work = Context.objects.create(owner=other_user, name='Alice Work')
        alice_ctx = Context.objects.create(owner=other_user, name='Alice Ctx')
        alice_identity = IdentityProfile.objects.create(owner=other_user, context=alice_work, identity_name='Alice Only')
        alice_rule = DisclosureRule.objects.create(
            identity=alice_identity, context=alice_ctx, field_name='identity_name', is_visible=True,
        )
        url = reverse('disclosure-rule-retrieve-update-destroy-api', kwargs={'pk': alice_rule.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  ## should return 404 Not Found

    def test_cannot_edit_another_users_rule(self):  ## same ownership protection extends to update
        other_user = User.objects.create_user(username='alice', password='testpass123')
        alice_work = Context.objects.create(owner=other_user, name='Alice Work')
        alice_ctx = Context.objects.create(owner=other_user, name='Alice Ctx')
        alice_identity = IdentityProfile.objects.create(owner=other_user, context=alice_work, identity_name='Alice Only')
        alice_rule = DisclosureRule.objects.create(
            identity=alice_identity, context=alice_ctx, field_name='identity_name', is_visible=False,
        )
        url = reverse('disclosure-rule-retrieve-update-destroy-api', kwargs={'pk': alice_rule.pk})
        response = self.client.patch(url, {'is_visible': True})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  ## should return 404 Not Found

    def test_cannot_delete_another_users_rule(self):  ## and to delete
        other_user = User.objects.create_user(username='alice', password='testpass123')
        alice_work = Context.objects.create(owner=other_user, name='Alice Work')
        alice_ctx = Context.objects.create(owner=other_user, name='Alice Ctx')
        alice_identity = IdentityProfile.objects.create(owner=other_user, context=alice_work, identity_name='Alice Only')
        alice_rule = DisclosureRule.objects.create(
            identity=alice_identity, context=alice_ctx, field_name='identity_name', is_visible=True,
        )
        url = reverse('disclosure-rule-retrieve-update-destroy-api', kwargs={'pk': alice_rule.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  ## should return 404 Not Found
        self.assertTrue(DisclosureRule.objects.filter(pk=alice_rule.pk).exists())


class DisclosureEngineTests(AuthenticatedAPITestCase):
    """self.user (john, from base) is the profile owner throughout; self.viewer
    (alice) is who's looking. Exercises the actual union-based engine
    end-to-end via /api/profile/<username>/ -- not just that rule rows
    can be created, but that they actually gate (or don't gate) content."""

    def setUp(self):
        super().setUp()
        self.viewer = User.objects.create_user(username='alice', password='testpass123')
        self.work_context = Context.objects.create(owner=self.user, name='Work')
        self.personal_context = Context.objects.create(owner=self.user, name='Personal')
        self.work_identity = IdentityProfile.objects.create(
            owner=self.user, context=self.work_context,
            identity_name='Work Me', description='Backend developer.',
        )
        self.personal_identity = IdentityProfile.objects.create(
            owner=self.user, context=self.personal_context,
            identity_name='Personal Me', description='Weekend hiker.',
        )
        self.profile_url = reverse('profile-api', kwargs={'username': self.user.username})

    def test_owner_sees_own_full_profile_regardless_of_rules(self):
        # self.user is still the authenticated client here -- no rules exist
        # at all, yet the owner should see everything (owner == viewer
        # bypasses disclosure filtering entirely).
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {i['visible_fields']['identity_name'] for i in response.data['visible_identities']}
        self.assertEqual(names, {'Work Me', 'Personal Me'})

    def test_stranger_with_no_relationship_and_no_public_rule_sees_nothing(self):
        self.authenticate_as(self.viewer)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['visible_identities'], [])

    def test_stranger_sees_public_tagged_field_with_no_relationship(self):
        # No relationship at all -- this is purely the auto-granted Public
        # context from get_effective_contexts.
        public_context = Context.objects.create(owner=self.user, name='Public', is_public_default=True)
        DisclosureRule.objects.create(
            identity=self.work_identity, context=public_context,
            field_name='identity_name', is_visible=True,
        )

        self.authenticate_as(self.viewer)
        response = self.client.get(self.profile_url)

        visible = response.data['visible_identities']
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0]['visible_fields'], {'identity_name': 'Work Me'})

    def test_relationship_reveals_fields_matching_tagged_context(self):
        colleague_context = Context.objects.create(owner=self.user, name='Colleague')
        relationship = Relationship.objects.create(owner=self.user, target_user=self.viewer)
        relationship.contexts.set([colleague_context])
        DisclosureRule.objects.create(
            identity=self.work_identity, context=colleague_context, field_name='identity_name', is_visible=True,
        )
        DisclosureRule.objects.create(
            identity=self.work_identity, context=colleague_context, field_name='description', is_visible=True,
        )

        self.authenticate_as(self.viewer)
        response = self.client.get(self.profile_url)

        visible = response.data['visible_identities']
        self.assertEqual(len(visible), 1)  # personal identity stays hidden -- no rule targets it under Colleague
        self.assertEqual(visible[0]['visible_fields'], {
            'identity_name': 'Work Me', 'description': 'Backend developer.',
        })

    def test_field_without_a_matching_rule_stays_hidden(self):
        colleague_context = Context.objects.create(owner=self.user, name='Colleague')
        relationship = Relationship.objects.create(owner=self.user, target_user=self.viewer)
        relationship.contexts.set([colleague_context])
        DisclosureRule.objects.create(
            identity=self.work_identity, context=colleague_context, field_name='identity_name', is_visible=True,
        )
        # description deliberately has no rule at all

        self.authenticate_as(self.viewer)
        response = self.client.get(self.profile_url)

        visible = response.data['visible_identities'][0]['visible_fields']
        self.assertIn('identity_name', visible)
        self.assertNotIn('description', visible)

    def test_is_visible_false_keeps_field_hidden(self):
        colleague_context = Context.objects.create(owner=self.user, name='Colleague')
        relationship = Relationship.objects.create(owner=self.user, target_user=self.viewer)
        relationship.contexts.set([colleague_context])
        DisclosureRule.objects.create(
            identity=self.work_identity, context=colleague_context, field_name='identity_name', is_visible=False,
        )

        self.authenticate_as(self.viewer)
        response = self.client.get(self.profile_url)

        self.assertEqual(response.data['visible_identities'], [])

    def test_union_rule_two_relationship_tags_reveal_fields_from_both(self):
        # The core design principle: a second context tag on a relationship
        # ADDS visibility, never revokes what the first tag already granted.
        # A single relationship, tagged twice, unlocks two separate identities.
        colleague_context = Context.objects.create(owner=self.user, name='Colleague')
        friend_context = Context.objects.create(owner=self.user, name='Friend')
        relationship = Relationship.objects.create(owner=self.user, target_user=self.viewer)
        relationship.contexts.set([colleague_context, friend_context])

        DisclosureRule.objects.create(
            identity=self.work_identity, context=colleague_context, field_name='identity_name', is_visible=True,
        )
        DisclosureRule.objects.create(
            identity=self.personal_identity, context=friend_context, field_name='description', is_visible=True,
        )

        self.authenticate_as(self.viewer)
        response = self.client.get(self.profile_url)

        visible = response.data['visible_identities']
        self.assertEqual(len(visible), 2)
        fields_by_identity = {v['identity_id']: v['visible_fields'] for v in visible}
        self.assertEqual(fields_by_identity[self.work_identity.pk], {'identity_name': 'Work Me'})
        self.assertEqual(fields_by_identity[self.personal_identity.pk], {'description': 'Weekend hiker.'})


class RelationshipPreviewAPITests(AuthenticatedAPITestCase):
    """Covers RelationshipPreviewAPIView -- reuses get_visible_identities
    with (request.user, relationship.target_user) instead of
    (profile_owner, request.user), so this proves the same engine from the
    owner's side: 'what would they see right now'."""

    def setUp(self):
        super().setUp()
        self.viewer = User.objects.create_user(username='alice', password='testpass123')
        self.work_context = Context.objects.create(owner=self.user, name='Work')
        self.colleague_context = Context.objects.create(owner=self.user, name='Colleague')
        self.identity = IdentityProfile.objects.create(
            owner=self.user, context=self.work_context,
            identity_name='Work Me', description='Backend developer.',
        )
        self.relationship = Relationship.objects.create(owner=self.user, target_user=self.viewer)
        self.relationship.contexts.set([self.colleague_context])
        DisclosureRule.objects.create(
            identity=self.identity, context=self.colleague_context, field_name='identity_name', is_visible=True,
        )
        self.url = reverse('relationship-preview-api', kwargs={'pk': self.relationship.pk})

    def test_preview_matches_what_target_user_would_see(self):
        # self.user (john, the relationship owner) is still authenticated --
        # previewing your own relationship doesn't require switching identity.
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['viewed_as'], 'alice')
        visible = response.data['visible_identities']
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0]['visible_fields'], {'identity_name': 'Work Me'})

    def test_cannot_preview_another_users_relationship(self):
        bob = User.objects.create_user(username='bob', password='testpass123')
        alice_ctx = Context.objects.create(owner=self.viewer, name='Alice Ctx')
        alice_relationship = Relationship.objects.create(owner=self.viewer, target_user=bob)
        alice_relationship.contexts.set([alice_ctx])

        url = reverse('relationship-preview-api', kwargs={'pk': alice_relationship.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  ## should return 404 Not Found

# TODO:
# list own rules --> 200
# create rule --> 201
# update visibility --> 200
# delete rule --> 204
# cannot use another user's identity or context --> 400
# cannot use public context --> 400 
# cannot retrieve another user's rule --> 404
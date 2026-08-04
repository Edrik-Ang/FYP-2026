## base.py -- shared test setup for authentication and identity management tests.
## AuthenticatedAPITestCase creates a logged in user and attaches a JWT access token to every request via APIClient, 
## so Context/Identity/Relationship/DisclosureRules dont need to reimplement the same login setup for every test case.
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class AuthenticatedAPITestCase(APITestCase):
    """ self.user is authenticated through each request made by self.client, for the duration of the test case.
    Call authenticate_as(other_user) to switch identity mid-test, 
    used for 404/403 on someone else's resource' tests every group plans to implement. 
    """
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='john', password='testpass123')
        self.authenticate_as(self.user)

    def authenticate_as(self, user):
        """Switch the authenticated user for the test client."""
        access = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
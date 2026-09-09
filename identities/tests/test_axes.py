# identities/tests/test_axes.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from axes.utils import reset

User = get_user_model()


class AxesLockoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='axestest', password='CorrectPassw0rd1', email='a@a.com')

    def tearDown(self):
        reset(username='axestest')  # avoid state leaking into other tests

    def test_lockout_after_five_failures_blocks_correct_password(self):
        for _ in range(5):
            self.client.post('/login/', {'username': 'axestest', 'password': 'wrongpassword'})

        response = self.client.post('/login/', {'username': 'axestest', 'password': 'CorrectPassw0rd1'})
        self.assertEqual(response.status_code, 429)

    def test_reset_on_success_clears_failure_count(self):
        for _ in range(3):
            self.client.post('/login/', {'username': 'axestest', 'password': 'wrongpassword'})

        # correct password on 4th attempt should succeed and reset the counter
        response = self.client.post('/login/', {'username': 'axestest', 'password': 'CorrectPassw0rd1'})
        self.assertEqual(response.status_code, 302)  # redirected to dashboard = logged in
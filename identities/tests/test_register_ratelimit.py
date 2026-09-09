from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterRatelimitTests(TestCase):
    def test_sixth_registration_attempt_in_hour_is_blocked(self):
        for i in range(5):
            response = self.client.post('/register/', {
                'username': f'testspam{i}',
                'email': f'testspam{i}@example.com',
                'password': 'Str0ngPassw0rd',
                'password2': 'Str0ngPassw0rd',
            })
            self.assertEqual(response.status_code, 302, f"attempt {i} should succeed")

        response = self.client.post('/register/', {
            'username': 'testspam5',
            'email': 'testspam5@example.com',
            'password': 'Str0ngPassw0rd',
            'password2': 'Str0ngPassw0rd',
        })
        self.assertEqual(response.status_code, 403)
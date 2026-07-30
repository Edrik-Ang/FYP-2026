## tokens.py file handle Email and password verification tokens using Hash-based Message Authentication Code (HMAC) and Django's built-in token generation utilities.

from django.contrib.auth.tokens import PasswordResetTokenGenerator

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """ Separate from Django's default token: invalidates on is_active/email
      change rather than password change, which fits verification better """
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}{user.email}"

email_verification_token = EmailVerificationTokenGenerator()
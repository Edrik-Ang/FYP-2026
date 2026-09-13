## /identities/services/account_service.py
## handle email change, password change account deletion. Separate from AuthService which has authentication handshake.
from .auth_service import AuthService


class AccountService:
    @staticmethod
    def change_email(user, new_email):
        """Change email for a user, no verification step, just change and save."""
        user.email = new_email
        user.save(update_fields=['email'])
        AuthService.blacklist_all_tokens_for_user(user)
        return user

    @staticmethod
    def change_password(user, new_password):
        """Change password and revoke all outstanding refresh token -- same pattern as password reset. """
        user.set_password(new_password)
        user.save(update_fields=['password'])
        AuthService.blacklist_all_tokens_for_user(user)
        return user

    @staticmethod
    def delete_account(user):
        """ Hard delete user account. and Everyting under it (UserProfile, Contexts, Relationships, etc) will be cascade deleted. 
        Respects user privacy and GDPR. Relationship.target_user and ConnetionRequest.sender/recipient also CASCADE, so rows other users hold referencing this also siliently removed, rather than reassigned.
        """
        user.delete()

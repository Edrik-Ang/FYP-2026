from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model

from django_rest_passwordreset.signals import reset_password_token_created, post_password_reset

from .models import Context, UserProfile
from identities.serializers import User
from .services.auth_service import AuthService

user = get_user_model()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    context = {
        'current_user': reset_password_token.user,
        'username': reset_password_token.user.username,
        'email': reset_password_token.user.email,
        'reset_password_url': "{}?token={}".format(
            instance.request.build_absolute_uri(reverse('password_reset_api:reset-password-confirm')),
            reset_password_token.key,
        ),
    }

    email_html_message = render_to_string('email/user_reset_password.html', context)
    email_plaintext_message = render_to_string('email/user_reset_password.txt', context)

    msg = EmailMultiAlternatives(
        "Password Reset Request",
        email_plaintext_message,
        settings.DEFAULT_FROM_EMAIL,
        [reset_password_token.user.email],
    )
    msg.attach_alternative(email_html_message, "text/html")
    msg.send()


@receiver(post_password_reset)
def password_reset_post(sender, user, *args, **kwargs):
    """ After successful password reset, blacklist all outstanding refresh tokens for the user to log them out of all sessions. """
    AuthService.blacklist_all_tokens_for_user(user)


@receiver(post_save, sender=User)
def provision_user_defaults(sender, instance, created, **kwargs):
    """ Fires when new user created, regardless of call site -- registration endpoint, web register_view, admin panel, shell, management command.
    Provisions the two account-level defaults to every user needs:
       - UserProfile (is_discoverable=True)
       - reserved system Context named 'Public' (is_system=True),
         the DisclosureService treats as always-visible to strangers per union rule.
    get_or_create ensures doesnt re-run (e.g password reset, admin edit) and create duplicates.
    """
    if not created:
        return
    UserProfile.objects.get_or_create(user=instance)
    Context.objects.get_or_create(owner=instance, is_system=True, defaults={'name': 'Public'})
## /identities/security/provider_response_errors.py
"""
Basically translates provider HTTP response codes into user-facing messages, and logs the details server-side for debugging.
Meant for calls that use stored per-user access token, where a 401 error means "token dead, user must reconnect",
not a transient failure worth retrying. Not meant for Steam's private-data sub resource fetches (owned games, wishlist, etc)
it degrades to visible=False than raise ValidationError, see steam_service.py for that logic.
"""
from http import HTTPStatus
import logging
import requests
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


def raise_for_provider_response(response, provider, context=""):
    """ Checks a provider's HTTP response and raise specific ValidationError for common failure cases,
    logging the cause server-side first."""
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        logger.warning("%s returned 401 (%s) -- token likely expired/revoked", provider, context)
        raise ValidationError(f"Your {provider} connection has expired. Please reconnect your account.")
    if response.status_code == HTTPStatus.FORBIDDEN:
        logger.warning("%s returned 403 (%s) -- likely rate-limited or forbidden", provider, context)
        raise ValidationError(f"{provider} rate limit reached. Please try again shortly.")
    if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:  # 500 -- still a clean named constant, just used as a range boundary
        logger.warning("%s returned %s (%s) -- provider-side error", provider, response.status_code, context)
        raise ValidationError(f"{provider} is currently unavailable. Please try again later.")

    try:
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("%s unexpected HTTP error (%s)", provider, context)
        raise ValidationError(f"Unable to complete the {provider} request. Please try again.")


def raise_for_network_error(exception, provider, context=""):
    """Call from except (Timeout, connectionError) around a provider request. 
    when request never got a response at all.
    """
    if isinstance(exception, requests.exceptions.Timeout):
        logger.warning("%s request timed out (%s)", provider, context)
        raise ValidationError(f"{provider} request timed out. Please try again.")
    
    logger.exception("%s Could not connect to %s", provider, context)
    raise ValidationError(f"Unable to complete the {provider} request due to a network error. Please try again.")
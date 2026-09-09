""" 
/identities/security/error_handling.py
Centralised error handling for views that call external OAuth providers (Steam, Github, etc)

Validation Error -- raised deliberately by own service layer with hand-authored messages. Safe to show to user as is.

Anything else is unexpected failure (network timeout, malformed API response, library-internal exception).
Never shown to user as is; Logged with full detail server-side instead.
"""
import logging
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

## Wrapper decorator to catch and handle errors, input params: name of view to redirect to, name of provider (Steam, Github, etc.)
def handle_integration_errors(redirect_to, provider):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request,  *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except ValidationError as e:
                detail = e.detail[0] if isinstance(e.detail, list) else e.detail
                messages.error(request, f"{provider} error: {detail}")
                return redirect(redirect_to)
            except Exception:
                logger.exception(
                    "Unexpected %s integration for user %s",
                    provider, request.user.id,
                )
                messages.error(
                    request, 
                    f"something went wrong connecting to {provider}. Please try again later."
                )
                return redirect(redirect_to)
        return wrapper
    return decorator
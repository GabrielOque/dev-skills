"""
Session issuing shared by every way in (password, refresh, activation,
password reset and any provider added later). They all end the same way:
the backend validates the account and issues its own JWT pair plus the
session payload.
"""

from django.contrib.auth.models import update_last_login
from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import ValidationCode
from accounts.services import issue_validation_code
from users.services import session_payload


class PasswordChangeRequired(APIException):
    """403 carrying a fresh reset code; the frontend sends the person to
    /reset-password/{reset_code}."""

    status_code = status.HTTP_403_FORBIDDEN
    default_code = "PASSWORD_CHANGE_REQUIRED"


def validate_login_user(django_user, enforce_password_change=False):
    """
    The checks every flow runs before handing out (or refreshing) a session.

    Holding a role is deliberately *not* required: access is decided per
    endpoint by `@required_perms`.

    `enforce_password_change` is only set by the password login: with
    `must_change_password` on, the session is withheld and a fresh
    password-reset code is returned instead. Other flows ignore the flag — a
    refresh keeps an existing session alive, and a reset is how the flag
    gets cleared.
    """
    profile = getattr(django_user, "profile", None)
    if profile is None:
        raise AuthenticationFailed(
            {"code": "NO_PROFILE", "message": "This account has no profile in the application"}
        )
    if not django_user.is_active:
        raise AuthenticationFailed({"code": "INACTIVE_USER", "message": "The account is not active"})
    if profile.archived or profile.organization.archived:
        raise AuthenticationFailed(
            {"code": "USER_OR_ORGANIZATION_ARCHIVED", "message": "The user or its organization is deactivated"}
        )
    if enforce_password_change and django_user.must_change_password:
        reset_code = issue_validation_code(django_user, ValidationCode.Purpose.PASSWORD_RESET)
        raise PasswordChangeRequired(
            {
                "code": "PASSWORD_CHANGE_REQUIRED",
                "message": "A new password must be set before signing in",
                "reset_code": reset_code,
            }
        )
    return django_user


def issue_session(django_user):
    """`{"access", "refresh", "user", "organization"}` for a validated user.
    Flows other than the password login stamp `last_login` themselves."""
    update_last_login(None, django_user)
    refresh = RefreshToken.for_user(django_user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        **session_payload(django_user),
    }

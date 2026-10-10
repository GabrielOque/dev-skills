"""
Credential lifecycle shared by the admin-driven and the public flows:
email normalization, single-use codes, the activation and password-reset
emails, and the password policy.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from common.services.email import send_templated_email

from .models import ValidationCode

Purpose = ValidationCode.Purpose


def normalize_email(value):
    """Emails are logins: compared and stored trimmed and lowercased."""
    return (value or "").strip().lower()


# ---------------------------------------------------------------------------
# Single-use codes
# ---------------------------------------------------------------------------
def issue_validation_code(django_user, purpose, ttl=None):
    """Create (or replace) the user's code for `purpose`. Returns the code."""
    code = secrets.token_urlsafe(32)
    expires_at = timezone.now() + (ttl or timedelta(hours=settings.VALIDATION_CODE_HOURS))
    ValidationCode.objects.update_or_create(
        django_user=django_user,
        purpose=purpose,
        defaults={"code": code, "expires_at": expires_at},
    )
    return code


def resolve_validation_code(code, purpose):
    """
    `(validation, error_code)` for a code submitted by the public flows.
    Exactly one of the two is set; error_code is INVALID_CODE or EXPIRED_CODE.
    """
    code = (code or "").strip()
    if not code:
        return None, "MISSING_CODE"
    validation = (
        ValidationCode.objects.select_related("django_user")
        .filter(code=code, purpose=purpose)
        .first()
    )
    if validation is None:
        return None, "INVALID_CODE"
    if validation.is_expired():
        return None, "EXPIRED_CODE"
    return validation, None


# ---------------------------------------------------------------------------
# Emails
# ---------------------------------------------------------------------------
def _link(path, code):
    return f"{settings.FRONTEND_URL}/{path}/{code}"


def send_activation_email(django_user):
    """Email a fresh activation link. Every call invalidates the previous one."""
    code = issue_validation_code(django_user, Purpose.ACTIVATION)
    return send_templated_email(
        to=django_user.email,
        subject=f"Activa tu cuenta en {settings.PROJECT_NAME}",
        template_name="emails/account_activation.html",
        context={
            "first_name": django_user.first_name,
            "link": _link("activate-account", code),
            "hours": settings.VALIDATION_CODE_HOURS,
            "project_name": settings.PROJECT_NAME,
        },
    )


def send_password_reset_email(django_user):
    """Email a fresh reset link. Every call invalidates the previous one."""
    code = issue_validation_code(django_user, Purpose.PASSWORD_RESET)
    return send_templated_email(
        to=django_user.email,
        subject=f"Restablece tu contraseña de {settings.PROJECT_NAME}",
        template_name="emails/password_reset.html",
        context={
            "first_name": django_user.first_name,
            "link": _link("reset-password", code),
            "hours": settings.VALIDATION_CODE_HOURS,
            "project_name": settings.PROJECT_NAME,
        },
    )


# ---------------------------------------------------------------------------
# Password policy — mirrored by the frontend in `libs/validators.ts`
# ---------------------------------------------------------------------------
SPECIAL_CHARACTERS = "!@#$%^&*(),.?\":{}|<>_-+=;'/\\[]~`"

PASSWORD_RULES = (
    ("min_length", lambda password: len(password) >= 8),
    ("uppercase", lambda password: any(char.isupper() for char in password)),
    ("lowercase", lambda password: any(char.islower() for char in password)),
    ("digit", lambda password: any(char.isdigit() for char in password)),
    ("special", lambda password: any(char in SPECIAL_CHARACTERS for char in password)),
)


def password_policy_failures(password, django_user=None):
    """
    The rule keys the password fails — empty when it passes. The frontend
    shows the same checklist; Django's validators (common or too similar to
    the user's data) report as `not_allowed`.
    """
    password = password or ""
    failures = [key for key, check in PASSWORD_RULES if not check(password)]
    if not failures:
        try:
            validate_password(password, user=django_user)
        except ValidationError:
            failures.append("not_allowed")
    return failures

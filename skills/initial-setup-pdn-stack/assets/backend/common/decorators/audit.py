"""Request auditing for views — see `audit_action`."""

import logging
from functools import wraps
from urllib.parse import parse_qsl, urlencode

from django.apps import apps

logger = logging.getLogger(__name__)

# Only state-changing verbs are recorded.
MUTATING_METHODS = ("POST", "PUT", "PATCH", "DELETE")

# Keys never stored, at any nesting level. Two tiers because redaction is
# destructive and over-matching silently destroys legitimate data.
# Substring match: unambiguous anywhere in a key ("new_password", "X-Api-Key").
SENSITIVE_KEY_HINTS = (
    "password",
    "passwd",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "id_token",
    "client_secret",
    "secret_key",
    "private_key",
    "authorization",
)
# Exact match: generic words that are only secrets when they are the whole key.
# Not "code": it is the error code of every API response.
SENSITIVE_KEYS_EXACT = frozenset(
    {"access", "refresh", "token", "secret", "auth", "pwd", "credentials", "reset_code"}
)
# Suffix match: anything ending in "_token".
SENSITIVE_KEY_SUFFIXES = ("_token",)

REDACTED = "***"
MAX_STRING_LENGTH = 5000
MAX_ENDPOINT_LENGTH = 500

# Optional headers the frontend may send to record where a call came from.
LATITUDE_HEADER = "X-Latitude"
LONGITUDE_HEADER = "X-Longitude"


def _is_sensitive(key):
    normalized = str(key).lower().replace("-", "_").replace(" ", "_")
    return (
        normalized in SENSITIVE_KEYS_EXACT
        or normalized.endswith(SENSITIVE_KEY_SUFFIXES)
        or any(hint in normalized for hint in SENSITIVE_KEY_HINTS)
    )


def _sanitize(value, depth=0):
    """Redact secrets, describe uploaded files instead of embedding them, and
    truncate huge strings."""
    if depth > 10:
        return "<max depth>"
    if isinstance(value, dict):
        return {
            key: (REDACTED if _is_sensitive(key) else _sanitize(item, depth + 1))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item, depth + 1) for item in value]
    if hasattr(value, "read") and hasattr(value, "name"):
        return {
            "file": getattr(value, "name", None),
            "size": getattr(value, "size", None),
            "content_type": getattr(value, "content_type", None),
        }
    if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
        return value[:MAX_STRING_LENGTH] + "…"
    return value


def _safe_endpoint(request):
    """Full path with the query string, sensitive params redacted."""
    path, separator, query = request.get_full_path().partition("?")
    if not separator:
        return path[:MAX_ENDPOINT_LENGTH]
    pairs = [
        (key, REDACTED if _is_sensitive(key) else value)
        for key, value in parse_qsl(query, keep_blank_values=True)
    ]
    return f"{path}?{urlencode(pairs, safe='[]*')}"[:MAX_ENDPOINT_LENGTH]


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _coordinate(request, header):
    try:
        return float(request.headers.get(header))
    except (TypeError, ValueError):
        return None


def _record(request, response_data, status_code):
    django_user = getattr(request, "user", None)
    if not getattr(django_user, "is_authenticated", False):
        django_user = None
    profile = getattr(django_user, "profile", None) if django_user else None

    apps.get_model("audit", "AuditLog").objects.create(
        endpoint=_safe_endpoint(request),
        method=request.method,
        status_code=500 if status_code is None else status_code,
        ip_address=_client_ip(request),
        latitude=_coordinate(request, LATITUDE_HEADER),
        longitude=_coordinate(request, LONGITUDE_HEADER),
        django_user=django_user,
        organization_id=getattr(profile, "organization_id", None),
        payload=_sanitize(getattr(request, "data", None)),
        response=_sanitize(response_data),
    )


def _safe_record(request, response_data, status_code):
    """Auditing never breaks the endpoint: any failure is logged and swallowed."""
    try:
        _record(request, response_data, status_code)
    except Exception:
        try:
            logger.exception("audit_action: could not record the call")
        except Exception:
            pass


def audit_action(view_func=None):
    """
    Record the call in `audit.AuditLog` when it changes state (POST, PUT,
    PATCH, DELETE — checked on the HTTP method, so custom `@action`s count).

    Put it **outermost**, above `@required_perms` and `@transaction.atomic`.

    Guarantees:
    - never breaks the endpoint;
    - never stores secrets (passwords, tokens, codes) nor file contents;
    - records rejections (4xx) and crashes (5xx) too;
    - one request, one row: DRF routes PATCH through `partial_update` →
      `update`, both audited; the outermost decorated call claims the request.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(view_instance, request, *args, **kwargs):
            if getattr(request, "_audit_claimed", False):
                return func(view_instance, request, *args, **kwargs)
            try:
                request._audit_claimed = True
            except Exception:
                pass

            is_mutating = getattr(request, "method", None) in MUTATING_METHODS
            try:
                response = func(view_instance, request, *args, **kwargs)
            except Exception as exc:
                if is_mutating:
                    # DRF exceptions (validation, 403, 404…) carry their own
                    # status; anything else is a crash.
                    _safe_record(
                        request,
                        {"error": exc.__class__.__name__, "detail": getattr(exc, "detail", str(exc))},
                        getattr(exc, "status_code", 500),
                    )
                raise

            if is_mutating:
                _safe_record(
                    request,
                    getattr(response, "data", None),
                    getattr(response, "status_code", None),
                )
            return response

        return wrapper

    if callable(view_func):
        return decorator(view_func)
    return decorator

"""
Permission gating for views — see `required_perms`.

Access control is permission-based, never role-based: a role is only a named
bundle of permissions. A user's effective permissions are the union of
every active role they hold plus the permissions granted to them directly.
Nothing can subtract a permission.
"""

import logging
from functools import wraps

from django.apps import apps
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

# Reserved keyword: any authenticated user may call the action.
NONE = "None"

AUTHENTICATION_REQUIRED = {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication credentials were not provided",
}
PERMISSION_DENIED = {
    "code": "PERMISSION_DENIED",
    "message": "You don't have permission to perform this action",
}


def get_effective_permission_codenames(django_user):
    """
    Every permission codename the user effectively holds, as a set.

    - Union of the permissions of every non-archived role the user holds and
      the permissions granted to them directly.
    - Archived permissions grant nothing, from any source.
    - A superuser holds every permission there is. Callers that *report*
      permissions (the login payload) rely on this: answering
      `is_superuser: true` next to an empty list would hide the whole UI from
      the one account allowed to see all of it.

    Models are resolved at call time so `common` never imports an app at
    module level.
    """
    Permission = apps.get_model("users", "Permission")
    active = Permission.objects.filter(archived=False)

    if django_user.is_superuser:
        return set(active.values_list("name", flat=True))

    profile = getattr(django_user, "profile", None)
    if profile is None:
        return set()

    return set(
        active.filter(Q(users=profile) | Q(roles__users=profile, roles__archived=False))
        .values_list("name", flat=True)
        .distinct()
    )


def _normalize(perms):
    """
    Exactly two accepted shapes — `"None"` or a list of codenames — checked at
    import time, so a malformed declaration never reaches production.
    """
    if perms == NONE:
        return (NONE,)
    if isinstance(perms, (list, tuple, set)) and perms:
        invalid = [perm for perm in perms if not isinstance(perm, str) or not perm]
        if invalid:
            raise TypeError(f"Permission codenames must be non-empty strings, got {invalid!r}")
        return tuple(perms)
    raise TypeError(
        'Expected "None" or a non-empty list of codenames, e.g. '
        '@required_perms(["module.resource.view"]) — got ' + repr(perms)
    )


def _gate(perms, mode):
    required = _normalize(perms)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(view_instance, request, *args, **kwargs):
            django_user = getattr(request, "user", None)
            if not django_user or not django_user.is_authenticated:
                return Response(AUTHENTICATION_REQUIRED, status=status.HTTP_401_UNAUTHORIZED)

            if NONE in required or django_user.is_superuser:
                return view_func(view_instance, request, *args, **kwargs)

            held = get_effective_permission_codenames(django_user)
            allowed = (
                all(perm in held for perm in required)
                if mode == "all"
                else any(perm in held for perm in required)
            )
            if not allowed:
                # The codenames go to the log, never to the caller: telling a
                # client which permission it lacks hands it a map of the
                # authorization model. The answer it is entitled to is "no".
                logger.info(
                    "permission denied: user=%s required(%s)=%s",
                    getattr(django_user, "id", None),
                    mode,
                    required,
                )
                return Response(PERMISSION_DENIED, status=status.HTTP_403_FORBIDDEN)

            return view_func(view_instance, request, *args, **kwargs)

        # Lets SecureViewSet / SecureModelViewSet verify the action is gated.
        wrapper._has_perms_decorator = True
        return wrapper

    return decorator


def required_perms(perms):
    """
    Gate a view on the project's own permissions (`users.Permission`).
    The user needs **all** the codenames listed (AND).

        @required_perms("None")                                # any signed-in user
        @required_perms(["access.users.view"])
        @required_perms(["access.users.create", "access.roles.view"])

    A codename that is not in the catalogue fixture can never be held, so the
    endpoint silently becomes superuser-only: add it to
    `users/fixtures/permissions_catalog.json` in the same change.

    Superusers bypass the check — Django's own full-access account and the
    only exception in the system.
    """
    return _gate(perms, mode="all")


def required_any_perms(perms):
    """Like `required_perms`, but the user needs **one** of the codenames (OR).
    For read endpoints that serve several screens with different gates."""
    return _gate(perms, mode="any")

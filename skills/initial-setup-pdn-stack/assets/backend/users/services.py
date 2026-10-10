"""
Business rules for the users, roles and permissions of an organization.

Views stay thin: they parse the request, call a service, and serialize the
result. Services raise `common.exceptions.ServiceError` with a stable code.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status

from accounts.services import normalize_email
from common.decorators import get_effective_permission_codenames
from common.exceptions import ServiceError

from .models import Permission, Role, User

DjangoUser = get_user_model()


# ---------------------------------------------------------------------------
# Session payload — the `user` / `organization` the frontend persists
# ---------------------------------------------------------------------------
def session_payload(django_user):
    """
    What every login, refresh and `GET me/` returns next to the tokens.

    `permissions` drives what the UI offers; it is never the authorization —
    the backend re-checks every request with `@required_perms`. `roles` are
    display labels only.
    """
    profile = django_user.profile
    organization = profile.organization
    full_name = f"{django_user.first_name} {django_user.last_name}".strip()
    return {
        "user": {
            "id": profile.id,
            "django_user_id": django_user.id,
            "email": django_user.email,
            "first_name": django_user.first_name,
            "last_name": django_user.last_name,
            "full_name": full_name or django_user.email,
            "roles": profile.role_names,
            "permissions": sorted(get_effective_permission_codenames(django_user)),
            "is_superuser": django_user.is_superuser,
            "must_change_password": django_user.must_change_password,
        },
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug,
        },
    }


# ---------------------------------------------------------------------------
# Roles and permissions
# ---------------------------------------------------------------------------
def resolve_roles(organization, role_ids):
    """Roles by id, **scoped to the organization**: a payload can never hand
    a user another tenant's role."""
    wanted = {str(role_id) for role_id in role_ids}
    roles = list(Role.objects.filter(organization=organization, id__in=wanted))
    if len(roles) != len(wanted):
        raise ServiceError("INVALID_ROLE", "One or more roles do not exist in the organization")
    return roles


def resolve_permissions(codenames):
    """Active permissions by codename. An archived permission grants nothing,
    so accepting it would only store a lie."""
    wanted = set(codenames)
    permissions = list(Permission.objects.filter(name__in=wanted, archived=False))
    if len(permissions) != len(wanted):
        raise ServiceError("INVALID_PERMISSION", "One or more permissions do not exist")
    return permissions


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@transaction.atomic
def invite_user(*, organization, email, first_name, last_name, role_ids=(), permission_codenames=()):
    """
    Create an inactive login (no usable password) and its profile. The caller
    sends the activation email once the transaction has committed.
    """
    email = normalize_email(email)
    if DjangoUser.objects.filter(username=email).exists():
        raise ServiceError("EMAIL_TAKEN", "A user with that email already exists", status.HTTP_409_CONFLICT)

    roles = resolve_roles(organization, role_ids)
    permissions = resolve_permissions(permission_codenames)

    django_user = DjangoUser(
        username=email,
        email=email,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        is_active=False,
    )
    django_user.set_unusable_password()
    django_user.save()

    profile = User.objects.create(django_user=django_user, organization=organization)
    profile.roles.set(roles)
    profile.permissions.set(permissions)
    return profile


@transaction.atomic
def update_user(profile, *, first_name=None, last_name=None, role_ids=None, permission_codenames=None):
    """Partial update: only the arguments that are not None change."""
    django_user = profile.django_user
    changed = []
    if first_name is not None:
        django_user.first_name = first_name.strip()
        changed.append("first_name")
    if last_name is not None:
        django_user.last_name = last_name.strip()
        changed.append("last_name")
    if changed:
        django_user.save(update_fields=changed)

    if role_ids is not None:
        profile.roles.set(resolve_roles(profile.organization, role_ids))
    if permission_codenames is not None:
        profile.permissions.set(resolve_permissions(permission_codenames))

    profile.save(update_fields=["updated_at"])
    return profile

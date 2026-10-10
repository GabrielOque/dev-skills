"""
Test helpers shared by every app's tests. Build exactly the data a test
needs — no fixtures with hidden state.

    organization = make_organization()
    owner = make_user(organization, "owner@example.com", permissions=["access.users.view"])
    client = authenticated_client(owner)
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

DEFAULT_PASSWORD = "Str0ng!Passw0rd"


def make_organization(name="Test organization"):
    from organizations.models import Organization

    return Organization.objects.create(name=name)


def make_permissions(*codenames):
    from users.models import Permission, permission_pk

    return [
        Permission.objects.get_or_create(
            name=codename,
            defaults={"id": permission_pk(codename), "description": codename},
        )[0]
        for codename in codenames
    ]


def make_role(organization, name, permissions=(), archived=False):
    from users.models import Role

    role = Role.objects.create(organization=organization, name=name, archived=archived)
    role.permissions.set(make_permissions(*permissions))
    return role


def make_user(
    organization,
    email,
    *,
    password=DEFAULT_PASSWORD,
    permissions=(),
    roles=(),
    is_active=True,
    is_superuser=False,
):
    """A login plus its business profile. Returns the profile (`users.User`)."""
    from users.models import User

    django_user = get_user_model().objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name="Test",
        last_name="User",
        is_active=is_active,
        is_superuser=is_superuser,
    )
    profile = User.objects.create(django_user=django_user, organization=organization)
    profile.permissions.set(make_permissions(*permissions))
    profile.roles.set(roles)
    return profile


def authenticated_client(profile):
    client = APIClient()
    token = RefreshToken.for_user(profile.django_user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client

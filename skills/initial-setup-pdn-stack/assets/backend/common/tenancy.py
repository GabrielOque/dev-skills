"""
Who is calling, inside the business model.

A login (`accounts.DjangoUser`) is not a business user: the business profile
(`users.User`, reachable as `django_user.profile`) carries the organization,
the roles and the permissions. These helpers are the one place views resolve
it, so a login without a profile (a bare `createsuperuser` account, which only
belongs in /admin) gets a clean 403 instead of an AttributeError.
"""

from rest_framework.exceptions import PermissionDenied

NO_PROFILE = {
    "code": "NO_PROFILE",
    "message": "This account has no profile in the application",
}


def get_profile(request):
    """The caller's `users.User`. Raises 403 NO_PROFILE when there is none."""
    profile = getattr(request.user, "profile", None)
    if profile is None:
        raise PermissionDenied(NO_PROFILE)
    return profile


def get_organization(request):
    return get_profile(request).organization


def get_organization_id(request):
    return get_profile(request).organization_id

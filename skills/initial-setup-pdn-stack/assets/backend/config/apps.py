from django.contrib.auth.apps import AuthConfig


class CustomAuthConfig(AuthConfig):
    """
    Installed instead of `django.contrib.auth` only to relabel its admin
    section.

    Django's `Group` and `Permission` are not part of this project's access
    control: roles and permissions are the project's own models
    (`users.Role`, `users.Permission`). The `auth_*` tables stay because the
    admin site and the auth machinery still rely on them.
    """

    verbose_name = "Django internals"

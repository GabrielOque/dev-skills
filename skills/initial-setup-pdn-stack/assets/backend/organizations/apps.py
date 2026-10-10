from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    """The tenant (`Organization`) and the `organization/current/` settings API."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "organizations"

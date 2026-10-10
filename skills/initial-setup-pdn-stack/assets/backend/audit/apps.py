from django.apps import AppConfig


class AuditConfig(AppConfig):
    """`AuditLog`, written by `@audit_action`. No API route."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"

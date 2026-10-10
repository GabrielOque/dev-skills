from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """`/api/auth/`: login, refresh, activation and password reset. No models."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "authentication"

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """The business profile (`User`), `Role` and the `Permission` catalogue."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """The login identity (`DjangoUser`) and its credential lifecycle."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

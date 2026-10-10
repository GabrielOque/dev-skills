from django.apps import AppConfig


class CommonConfig(AppConfig):
    """
    The base layer every app imports: `BaseModel`, secure viewsets,
    permission and audit decorators, the error contract and the listing
    plumbing. `common` never imports another project app at module level.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "common"

import uuid

from django.db import models

from common.models import BaseModel

# Permission primary keys are derived from the codename (uuid5), so the
# catalogue fixture is deterministic and `loaddata` is idempotent in every
# environment. Changing this namespace changes every pk: don't.
PERMISSION_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "urn:pdn:permission")


def permission_pk(codename):
    """The deterministic pk of a permission codename."""
    return uuid.uuid5(PERMISSION_NAMESPACE, codename)


class Permission(BaseModel):
    """
    One thing a user may do — the project's own catalogue, replacing
    `django.contrib.auth.models.Permission`.

    Django's permissions are generated per model (`add_/change_/delete_/
    view_<model>`); owning the catalogue lets a permission describe an
    *action* the product cares about (`billing.invoices.void`) rather than a
    table, and lets each organization compose its own roles from it.

    Nothing generates these rows: the source of truth is
    `users/fixtures/permissions_catalog.json`, applied with
    `python manage.py sync_permissions`. Codenames follow
    `<module>.<resource>.<action>`.
    """

    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Codename",
        help_text="Checked by @required_perms, e.g. 'access.users.view'.",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
        help_text="What it allows, in the words the person assigning it reads.",
    )

    @property
    def module(self):
        """The first segment of the codename. Derived, never stored."""
        return self.name.split(".", 1)[0]

    def __str__(self):
        return self.name

    class Meta:
        db_table = "permission"
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["name"]

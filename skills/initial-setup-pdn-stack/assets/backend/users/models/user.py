from django.conf import settings
from django.db import models

from common.models import BaseModel


class User(BaseModel):
    """
    The business profile of a login (`accounts.DjangoUser`, linked one-to-one
    and reachable as `django_user.profile`).

    Auth concerns stay on DjangoUser; everything the business cares about —
    the organization, roles, direct permissions, and any domain field the
    project adds later — lives here.

    Access = union of `roles` (inherited) and `permissions` (additional).
    Neither list can revoke the other.
    """

    django_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="profile",
        on_delete=models.CASCADE,
        verbose_name="Django user",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        related_name="users",
        on_delete=models.CASCADE,
        verbose_name="Organization",
    )
    roles = models.ManyToManyField(
        "users.Role",
        related_name="users",
        blank=True,
        verbose_name="Roles",
    )
    permissions = models.ManyToManyField(
        "users.Permission",
        related_name="users",
        blank=True,
        verbose_name="Additional permissions",
        help_text="Granted to this user directly, on top of their roles.",
    )

    @property
    def role_names(self):
        """Active role names, for display only — never for authorization."""
        return list(self.roles.filter(archived=False).order_by("name").values_list("name", flat=True))

    def __str__(self):
        return self.django_user.username

    class Meta:
        # "user" is a reserved word in PostgreSQL; this name keeps raw SQL
        # free of quoting.
        db_table = "user_profile"
        verbose_name = "User"
        verbose_name_plural = "Users"

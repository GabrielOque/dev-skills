from django.db import models

from common.models import BaseModel


class Role(BaseModel):
    """
    A named bundle of permissions, owned by one organization — what Django's
    `Group` would be if it could be scoped to a tenant (it can't:
    `auth_group.name` is globally unique, so two organizations could never
    both have an "Administrator").

    Roles are additive, never subtractive: a user's effective permissions are
    the union of every active role they hold plus the ones granted to them
    directly. Code never checks a role name — only permissions.

    Archiving a role keeps its assignments (reactivating restores them) but
    it stops granting anything.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        related_name="roles",
        on_delete=models.CASCADE,
        verbose_name="Organization",
    )
    name = models.CharField(max_length=150, verbose_name="Name")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    permissions = models.ManyToManyField(
        "users.Permission",
        related_name="roles",
        blank=True,
        verbose_name="Permissions",
    )

    def __str__(self):
        return self.name

    class Meta:
        db_table = "role"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="role_unique_name_per_organization",
            ),
        ]

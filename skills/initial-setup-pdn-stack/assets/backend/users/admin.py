from django.contrib import admin
from django.contrib.auth.models import Group

from common.admin import BaseModelAdmin

from .models import Permission, Role, User

# Django's Group is replaced by `users.Role` (the same idea, scoped to an
# organization). Leaving it registered would offer a second, tenant-blind
# place to manage roles that silently does nothing.
admin.site.unregister(Group)


@admin.register(Permission)
class PermissionAdmin(BaseModelAdmin):
    """The catalogue is owned by the fixture (`sync_permissions`); the admin
    is for reading it. Editing a codename here would desync every
    `@required_perms` that names it."""

    list_display = ["name", "description", "archived"]
    search_fields = ["name", "description"]
    fieldsets = (("Permission", {"fields": ("name", "description")}),)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        return readonly + ["name"] if obj else readonly


@admin.register(Role)
class RoleAdmin(BaseModelAdmin):
    list_display = ["name", "organization", "archived", "created_at"]
    list_filter = ["organization"]
    search_fields = ["name", "description", "organization__name"]
    filter_horizontal = ["permissions"]
    fieldsets = (
        ("Role", {"fields": ("organization", "name", "description")}),
        ("Permissions", {"fields": ("permissions",)}),
    )


@admin.register(User)
class UserAdmin(BaseModelAdmin):
    list_display = ["django_user", "organization", "archived", "created_at"]
    list_filter = ["organization"]
    search_fields = ["django_user__username", "django_user__first_name", "django_user__last_name"]
    filter_horizontal = ["roles", "permissions"]
    fieldsets = (
        ("Login", {"fields": ("django_user",)}),
        ("Organization", {"fields": ("organization",)}),
        (
            "Access",
            {
                "fields": ("roles", "permissions"),
                "description": (
                    "Effective access is the union of every active role's "
                    "permissions and the additional ones granted here."
                ),
            },
        ),
    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Only offer roles of the organization being edited."""
        if db_field.name == "roles":
            object_id = request.resolver_match.kwargs.get("object_id")
            profile = User.objects.filter(pk=object_id).first() if object_id else None
            if profile:
                kwargs["queryset"] = Role.objects.filter(organization_id=profile.organization_id)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

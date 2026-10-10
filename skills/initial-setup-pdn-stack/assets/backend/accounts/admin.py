from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import DjangoUser, ValidationCode


@admin.register(DjangoUser)
class DjangoUserAdmin(UserAdmin):
    """
    Django's stock UserAdmin minus the `groups` and `user_permissions`
    pickers. Those fields still exist on AbstractUser but nothing reads them:
    access comes from `users.Role` and `users.User.permissions`. Leaving them
    on screen would offer a second, tenant-blind place to grant access where
    whatever someone set would silently do nothing.
    """

    fieldsets = (
        (None, {"fields": ("username", "password", "must_change_password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Status",
            {
                "fields": ("is_active", "is_staff", "is_superuser"),
                "description": (
                    "Roles and permissions are managed on the business profile "
                    "(Users → Users). `is_superuser` bypasses every check."
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined", "password_changed_at")}),
    )
    readonly_fields = ("last_login", "date_joined", "password_changed_at")
    list_display = ("username", "first_name", "last_name", "is_active", "is_superuser", "last_login")
    list_filter = ("is_active", "is_staff", "is_superuser", "must_change_password")
    filter_horizontal = ()


@admin.register(ValidationCode)
class ValidationCodeAdmin(admin.ModelAdmin):
    list_display = ("django_user", "purpose", "expires_at", "created_at")
    list_filter = ("purpose",)
    search_fields = ("django_user__username",)
    # Codes are credentials: visible for support, never editable by hand.
    readonly_fields = ("django_user", "purpose", "code", "expires_at", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

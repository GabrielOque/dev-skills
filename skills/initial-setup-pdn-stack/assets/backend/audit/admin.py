from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only: an audit trail that can be edited is not an audit trail."""

    list_display = ["created_at", "organization", "django_user", "method", "endpoint", "status_code", "ip_address"]
    list_filter = ["method", "status_code", "organization"]
    search_fields = ["endpoint", "ip_address", "django_user__username"]
    date_hierarchy = "created_at"

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

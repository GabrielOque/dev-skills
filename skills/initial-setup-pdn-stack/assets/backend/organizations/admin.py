from django.contrib import admin

from common.admin import BaseModelAdmin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(BaseModelAdmin):
    list_display = ["name", "slug", "email", "phone", "archived", "created_at"]
    search_fields = ["name", "slug", "email"]
    fieldsets = (("Organization", {"fields": ("name", "slug", "email", "phone")}),)

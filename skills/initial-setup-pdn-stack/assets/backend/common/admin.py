from django.contrib import admin

SYSTEM_CONTROL = "System control"


class BaseModelAdmin(admin.ModelAdmin):
    """
    Admin base for models that inherit from `common.models.BaseModel`.

    Every admin gets the `archived` / `created_at` filters and a collapsed
    "System control" fieldset without redeclaring them.
    """

    readonly_fields = ["created_at", "updated_at"]

    def get_list_filter(self, request):
        own = list(self.list_filter or [])
        return own + [item for item in ("archived", "created_at") if item not in own]

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj) or [])
        if not any(name == SYSTEM_CONTROL for name, _ in fieldsets):
            fieldsets.append(
                (
                    SYSTEM_CONTROL,
                    {"fields": ("archived", "created_at", "updated_at"), "classes": ("collapse",)},
                )
            )
        return tuple(fieldsets)

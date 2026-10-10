from rest_framework import serializers

from ..models import Permission, Role


class RoleSerializer(serializers.ModelSerializer):
    """
    Permissions travel as codenames (`access.users.view`), never as ids:
    they are unique, stable and exactly what `@required_perms` checks.

    `organization` is not a field: the viewset stamps it from the caller, so
    a payload can never place a role in another tenant.
    """

    permissions = serializers.SlugRelatedField(
        many=True,
        slug_field="name",
        queryset=Permission.objects.filter(archived=False),
        required=False,
    )

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Required")
        return value

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions", "archived", "created_at", "updated_at"]
        read_only_fields = ["id", "archived", "created_at", "updated_at"]

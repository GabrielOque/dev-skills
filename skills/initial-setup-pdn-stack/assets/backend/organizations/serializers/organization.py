from rest_framework import serializers

from ..models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    """The caller's own organization. `slug` is read-only: it lives in links."""

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Required")
        return value

    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "email", "phone", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

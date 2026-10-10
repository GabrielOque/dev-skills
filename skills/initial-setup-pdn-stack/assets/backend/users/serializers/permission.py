from rest_framework import serializers

from ..models import Permission


class PermissionSerializer(serializers.ModelSerializer):
    """
    Read-only. The catalogue is defined by the backend (the fixture), never
    written through the API.
    """

    module = serializers.CharField(read_only=True)

    class Meta:
        model = Permission
        fields = ["id", "name", "module", "description"]
        read_only_fields = fields

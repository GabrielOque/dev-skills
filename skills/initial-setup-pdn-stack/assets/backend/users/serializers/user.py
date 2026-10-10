from rest_framework import serializers

from ..models import User

# What the UI calls the user's status, derived from two columns:
# `archived` (deactivated by an administrator) and `is_active` (finished the
# invitation).
STATUS_ACTIVE = "active"
STATUS_PENDING = "pending"
STATUS_INACTIVE = "inactive"


def user_status(profile):
    if profile.archived:
        return STATUS_INACTIVE
    return STATUS_ACTIVE if profile.django_user.is_active else STATUS_PENDING


class UserSerializer(serializers.ModelSerializer):
    """Read shape of a user: identity from the login, access from the profile."""

    email = serializers.EmailField(source="django_user.email", read_only=True)
    first_name = serializers.CharField(source="django_user.first_name", read_only=True)
    last_name = serializers.CharField(source="django_user.last_name", read_only=True)
    last_login = serializers.DateTimeField(source="django_user.last_login", read_only=True)
    status = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    permissions = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    def get_status(self, obj):
        return user_status(obj)

    def get_roles(self, obj):
        return [
            {"id": role.id, "name": role.name, "archived": role.archived}
            for role in obj.roles.order_by("name")
        ]

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "status",
            "last_login",
            "roles",
            "permissions",
            "archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserCreateSerializer(serializers.Serializer):
    """Payload to invite a user. Roles by id, permissions by codename."""

    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    roles = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    permissions = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class UserUpdateSerializer(serializers.Serializer):
    """Partial update. The email is the login and is not editable here."""

    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    roles = serializers.ListField(child=serializers.UUIDField(), required=False)
    permissions = serializers.ListField(child=serializers.CharField(), required=False)

from django.db.models import Q
from rest_framework.response import Response

from common.decorators import required_any_perms
from common.viewsets import SecureViewSet

from ..models import Permission
from ..serializers import PermissionSerializer


class PermissionViewSet(SecureViewSet):
    """
    `permissions/` — the catalogue, read-only and global: permissions describe
    what the application can gate, not what a tenant configured. It grows by
    release, not by usage, so it is returned whole; the UI groups and
    searches a list this size faster than another round trip would.
    """

    @required_any_perms(
        ["access.permissions.view", "access.roles.create", "access.roles.edit", "access.users.edit"]
    )
    def list(self, request):
        permissions = Permission.objects.filter(archived=False).order_by("name")

        module = request.GET.get("module", "")
        if module:
            # A prefix, not a substring: "billing" must not match "x.billing_y".
            permissions = permissions.filter(name__startswith=f"{module}.")

        search = request.GET.get("search", "")
        if search:
            permissions = permissions.filter(
                Q(name__unaccent__icontains=search) | Q(description__unaccent__icontains=search)
            )

        results = PermissionSerializer(permissions, many=True).data
        return Response({"results": results, "total_rows": len(results)})

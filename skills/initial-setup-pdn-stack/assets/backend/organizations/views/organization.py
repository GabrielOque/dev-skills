from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response

from common.decorators import audit_action, required_perms
from common.tenancy import get_organization
from common.viewsets import SecureViewSet

from ..serializers import OrganizationSerializer

PERM_VIEW = "organization.settings.view"
PERM_EDIT = "organization.settings.edit"

EDITABLE_FIELDS = ("name", "email", "phone")


class OrganizationViewSet(SecureViewSet):
    """
    `organization/current/` — always the caller's own organization, never
    addressed by id, so there is nothing to scope and nothing to leak.
    """

    @required_perms([PERM_VIEW])
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        return Response(OrganizationSerializer(get_organization(request)).data)

    @audit_action
    @required_perms([PERM_EDIT])
    @transaction.atomic
    @current.mapping.patch
    def update_current(self, request):
        organization = get_organization(request)
        data = {key: value for key, value in request.data.items() if key in EDITABLE_FIELDS}
        serializer = OrganizationSerializer(organization, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

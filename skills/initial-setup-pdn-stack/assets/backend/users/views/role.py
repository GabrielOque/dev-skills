from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response

from common.decorators import audit_action, required_any_perms, required_perms
from common.listing import (
    fetch_page,
    page_response,
    resolve_archived_filter,
    resolve_page,
    resolve_page_size,
)
from common.queries import build_where_clause
from common.tenancy import get_organization, get_organization_id
from common.viewsets import OrganizationScopedMixin, SecureModelViewSet, UniqueConflictMixin

from ..models import Role
from ..serializers import RoleSerializer

PERM_VIEW = "access.roles.view"
PERM_CREATE = "access.roles.create"
PERM_EDIT = "access.roles.edit"
PERM_DEACTIVATE = "access.roles.deactivate"

LIST_QUERY = """
    WITH permission_counts AS (
        SELECT rp.role_id, COUNT(*) AS permissions_count
        FROM role_permissions rp
        JOIN permission p ON p.id = rp.permission_id AND p.archived = false
        GROUP BY rp.role_id
    ),
    user_counts AS (
        SELECT ur.role_id, COUNT(*) AS users_count
        FROM user_profile_roles ur
        JOIN user_profile u ON u.id = ur.user_id AND u.archived = false
        GROUP BY ur.role_id
    )
    SELECT
        r.id,
        r.name,
        r.description,
        r.archived,
        r.created_at,
        COALESCE(pc.permissions_count, 0) AS permissions_count,
        COALESCE(uc.users_count, 0) AS users_count,
        COUNT(*) OVER() AS total_rows
    FROM role r
    LEFT JOIN permission_counts pc ON pc.role_id = r.id
    LEFT JOIN user_counts uc ON uc.role_id = r.id
    {where}
    ORDER BY r.name
    LIMIT %s OFFSET %s
"""


class RoleViewSet(UniqueConflictMixin, OrganizationScopedMixin, SecureModelViewSet):
    """
    `roles/` — the permission bundles each organization composes for itself
    from the catalogue. Deactivated, never deleted: a deactivated role keeps
    its assignments but stops granting.
    """

    queryset = Role.objects.prefetch_related("permissions")
    serializer_class = RoleSerializer
    conflict_code = "ROLE_NAME_TAKEN"
    conflict_message = "A role with that name already exists in the organization"

    def perform_create(self, serializer):
        serializer.save(organization=get_organization(self.request))

    @required_perms([PERM_VIEW])
    def list(self, request):
        page = resolve_page(request.GET.get("page"))
        page_size = resolve_page_size(request.GET.get("page_size"))
        _, where, params = build_where_clause(
            [
                {"type": "equal", "value": get_organization_id(request), "fields": ["r.organization_id"]},
                {"type": "search", "value": request.GET.get("search"), "fields": ["r.name", "r.description"]},
                {
                    "type": "boolean",
                    "value": resolve_archived_filter(request.GET.getlist("status[]")),
                    "fields": ["r.archived"],
                },
            ]
        )
        rows, total_rows = fetch_page(
            LIST_QUERY.format(where=where),
            [*params, page_size, (page - 1) * page_size],
        )
        return page_response(rows, total_rows, page, page_size)

    # Named `role_options`, routed as `options/`: a method called `options`
    # would shadow DRF's handler for the HTTP OPTIONS verb.
    @required_any_perms([PERM_VIEW, "access.users.create", "access.users.edit"])
    @action(detail=False, methods=["get"], url_path="options")
    def role_options(self, request):
        """
        Every active role with its permission codenames in one response — what
        the user editor needs to show which permissions each role grants
        without one request per role.
        """
        roles = (
            Role.objects.filter(organization_id=get_organization_id(request), archived=False)
            .prefetch_related("permissions")
            .order_by("name")
        )
        return Response(
            [
                {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "permissions": sorted(
                        permission.name for permission in role.permissions.all() if not permission.archived
                    ),
                }
                for role in roles
            ]
        )

    @required_perms([PERM_VIEW])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_CREATE])
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_EDIT])
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_EDIT])
    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_DEACTIVATE])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_DEACTIVATE])
    @action(detail=True, methods=["patch"])
    def restore(self, request, *args, **kwargs):
        return super().restore(request, *args, **kwargs)

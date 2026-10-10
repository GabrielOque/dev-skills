from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.services import send_activation_email, send_password_reset_email
from common.decorators import audit_action, required_perms
from common.listing import (
    fetch_page,
    page_response,
    parse_uuid_list,
    resolve_page,
    resolve_page_size,
)
from common.queries import build_where_clause
from common.tenancy import get_organization, get_organization_id
from common.viewsets import OrganizationScopedMixin, SecureModelViewSet

from ..models import User
from ..serializers import UserCreateSerializer, UserSerializer, UserUpdateSerializer
from ..services import invite_user, update_user

PERM_VIEW = "access.users.view"
PERM_CREATE = "access.users.create"
PERM_EDIT = "access.users.edit"
PERM_DEACTIVATE = "access.users.deactivate"

# `status[]` filter values → SQL. Selecting all or none constrains nothing.
STATUS_CONDITIONS = {
    "active": "(u.archived = false AND du.is_active = true)",
    "pending": "(u.archived = false AND du.is_active = false)",
    "inactive": "(u.archived = true)",
}

LIST_QUERY = """
    SELECT
        u.id,
        du.email,
        du.first_name,
        du.last_name,
        du.last_login,
        u.archived,
        u.created_at,
        CASE
            WHEN u.archived THEN 'inactive'
            WHEN du.is_active THEN 'active'
            ELSE 'pending'
        END AS status,
        -- Active roles only: an archived role no longer grants anything.
        COALESCE(
            (
                SELECT array_agg(r.name ORDER BY r.name)
                FROM user_profile_roles ur
                JOIN role r ON r.id = ur.role_id AND r.archived = false
                WHERE ur.user_id = u.id
            ),
            ARRAY[]::varchar[]
        ) AS roles,
        COUNT(*) OVER() AS total_rows
    FROM user_profile u
    JOIN django_user du ON du.id = u.django_user_id
    {where}
    ORDER BY du.first_name, du.last_name, du.email
    LIMIT %s OFFSET %s
"""


class UserViewSet(OrganizationScopedMixin, SecureModelViewSet):
    """
    `users/` — the people of the caller's organization.

    Creating a user invites them: an inactive login is created and an
    activation link is emailed. Users are deactivated (`archived`), never
    deleted; a deactivated user can no longer sign in or refresh a session.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    scope_select_related = ("django_user",)
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    @required_perms([PERM_VIEW])
    def list(self, request):
        page = resolve_page(request.GET.get("page"))
        page_size = resolve_page_size(request.GET.get("page_size"))
        statuses = request.GET.getlist("status[]")
        role_ids = parse_uuid_list(request.GET.getlist("roles[]"))

        clauses, _, params = build_where_clause(
            [
                {"type": "equal", "value": get_organization_id(request), "fields": ["u.organization_id"]},
                {
                    "type": "search",
                    "value": request.GET.get("search"),
                    "fields": ["du.email", "du.first_name", "du.last_name"],
                },
            ]
        )
        selected = [STATUS_CONDITIONS[value] for value in statuses if value in STATUS_CONDITIONS]
        if selected and len(selected) < len(STATUS_CONDITIONS):
            clauses.append("(" + " OR ".join(selected) + ")")
        if role_ids:
            clauses.append(
                "EXISTS (SELECT 1 FROM user_profile_roles fr WHERE fr.user_id = u.id AND fr.role_id = ANY(%s))"
            )
            params.append(role_ids)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        rows, total_rows = fetch_page(
            LIST_QUERY.format(where=where),
            [*params, page_size, (page - 1) * page_size],
        )
        return page_response(rows, total_rows, page, page_size)

    @required_perms([PERM_VIEW])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_CREATE])
    def create(self, request, *args, **kwargs):
        payload = UserCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        profile = invite_user(
            organization=get_organization(request),
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            role_ids=data["roles"],
            permission_codenames=data["permissions"],
        )
        # Sent after the user is committed: a failed email never rolls the
        # user back, and the response says whether it went out.
        sent = send_activation_email(profile.django_user)
        return Response(
            {**UserSerializer(profile).data, "invitation_sent": sent},
            status=status.HTTP_201_CREATED,
        )

    @audit_action
    @required_perms([PERM_EDIT])
    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        profile = self.get_object()
        payload = UserUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        update_user(
            profile,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            role_ids=data.get("roles"),
            permission_codenames=data.get("permissions"),
        )
        return Response(UserSerializer(profile).data)

    @audit_action
    @required_perms([PERM_DEACTIVATE])
    def destroy(self, request, *args, **kwargs):
        if self.get_object().django_user_id == request.user.id:
            return Response(
                {"code": "CANNOT_DEACTIVATE_SELF", "message": "You cannot deactivate your own user"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_DEACTIVATE])
    @action(detail=True, methods=["patch"])
    def restore(self, request, *args, **kwargs):
        return super().restore(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_EDIT])
    @action(detail=True, methods=["post"], url_path="resend-invitation")
    def resend_invitation(self, request, *args, **kwargs):
        """A fresh activation link; the previous one stops working."""
        profile = self.get_object()
        if profile.archived:
            return Response(
                {"code": "USER_ARCHIVED", "message": "The user is deactivated"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if profile.django_user.is_active:
            return Response(
                {"code": "ALREADY_ACTIVATED", "message": "The account is already activated"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not send_activation_email(profile.django_user):
            return Response(
                {"code": "EMAIL_NOT_SENT", "message": "The email could not be sent"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"code": "INVITATION_SENT", "message": "Invitation sent"})

    @audit_action
    @required_perms([PERM_EDIT])
    @action(detail=True, methods=["post"], url_path="send-password-reset")
    def send_password_reset(self, request, *args, **kwargs):
        """Email the user a reset link (an administrator never sees passwords)."""
        profile = self.get_object()
        if profile.archived or not profile.django_user.is_active:
            return Response(
                {"code": "INACTIVE_USER", "message": "The user is not active"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not send_password_reset_email(profile.django_user):
            return Response(
                {"code": "EMAIL_NOT_SENT", "message": "The email could not be sent"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"code": "PASSWORD_RESET_SENT", "message": "Password reset email sent"})

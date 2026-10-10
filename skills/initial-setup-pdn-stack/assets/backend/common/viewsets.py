"""
Base viewsets. Every endpoint of the project is built on one of these:

- `SecureViewSet` / `SecureModelViewSet` refuse to serve any action that is
  not decorated with `@required_perms` (or `@required_any_perms`), so an
  endpoint can never ship without explicit access control.
- `SecureModelViewSet.destroy` archives instead of deleting; `restore`
  reactivates.
- `OrganizationScopedMixin` scopes every queryset to the caller's
  organization (tenant isolation).
- `UniqueConflictMixin` turns unique-constraint clashes into a 409.

Fixed MRO for a resource: `class XViewSet(UniqueConflictMixin,
OrganizationScopedMixin, SecureModelViewSet)`.
"""

from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .tenancy import get_organization_id

DENIED = {"code": "PERMISSION_DENIED", "message": "You don't have permission to perform this action"}


def _enforce_perms_decorator(viewset):
    """
    Refuse an action that is not gated by a permission decorator.

    Checked at request time for everyone, superusers included: a missing
    decorator is a bug, not a permission problem, and it fails loudly instead
    of shipping an open endpoint.
    """
    request = getattr(viewset, "request", None)
    if request is not None and request.method.lower() not in viewset.http_method_names:
        return  # let DRF answer 405 METHOD_NOT_ALLOWED
    action_name = getattr(viewset, "action", None)
    if not action_name or not hasattr(viewset, action_name):
        return
    if not hasattr(getattr(viewset, action_name), "_has_perms_decorator"):
        raise ValidationError(
            {
                "code": "MISSING_PERMS_DECORATOR",
                "message": f"Action '{action_name}' must be decorated with @required_perms",
            }
        )


def _resolve_organization_id(viewset, obj):
    """
    The organization an instance belongs to: `obj.organization_id` when the
    model has it, otherwise `viewset.organization_id_getter(obj)` for models
    that reach the organization through a parent. Raises when neither exists,
    so a misconfigured viewset cannot silently skip the tenant check.
    """
    if hasattr(obj, "organization_id"):
        return obj.organization_id
    getter = getattr(viewset, "organization_id_getter", None)
    if callable(getter):
        return getter(obj)
    raise NotImplementedError(
        f"{obj.__class__.__name__} has no 'organization_id' and "
        f"{viewset.__class__.__name__} defines no 'organization_id_getter'."
    )


class SecureViewSet(viewsets.ViewSet):
    """ViewSet whose every action must declare its permissions."""

    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        _enforce_perms_decorator(self)


class SecureModelViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet whose every action must declare its permissions, with soft
    archiving instead of deletes.

    `destroy` and `restore` carry no decorator here on purpose: each subclass
    overrides them with its own `@required_perms` and delegates, so the
    codenames stay explicit per resource:

        @audit_action
        @required_perms(["module.resource.deactivate"])
        def destroy(self, request, *args, **kwargs):
            return super().destroy(request, *args, **kwargs)
    """

    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        _enforce_perms_decorator(self)

    def _assert_same_organization(self, request, obj):
        """Permissions say *what*; this says *whose*."""
        if _resolve_organization_id(self, obj) != get_organization_id(request):
            raise PermissionDenied(DENIED)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self._assert_same_organization(request, obj)
        if obj.archived:
            return Response(
                {"code": "ALREADY_ARCHIVED", "message": f"{obj.__class__.__name__} is already archived"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.archived = True
        obj.save(update_fields=["archived", "updated_at"])
        return Response(
            {"code": "ARCHIVED", "message": f"{obj.__class__.__name__} archived"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def restore(self, request, *args, **kwargs):
        obj = self.get_object()
        self._assert_same_organization(request, obj)
        if not obj.archived:
            return Response(
                {"code": "NOT_ARCHIVED", "message": f"{obj.__class__.__name__} is not archived"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.archived = False
        obj.save(update_fields=["archived", "updated_at"])
        return Response(self.get_serializer(obj).data, status=status.HTTP_200_OK)


class OrganizationScopedMixin:
    """
    Scopes every detail action to the caller's tenant. `get_object()` reads
    from `get_queryset()`, so this one filter covers retrieve, update,
    destroy and restore at once: another organization's record is simply not
    found (404, not 403 — its existence is not disclosed).

    - `organization_lookup`: ORM path to the organization
      (`"parent__organization_id"` for a child model).
    - `scope_filters`: permanent extra constraints.
    - `scope_select_related`: joins the serializer needs.
    """

    organization_lookup = "organization_id"
    scope_filters = {}
    scope_select_related = ()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.scope_select_related:
            queryset = queryset.select_related(*self.scope_select_related)
        return queryset.filter(
            **{self.organization_lookup: get_organization_id(self.request)},
            **self.scope_filters,
        )


class UniqueConflictMixin:
    """
    Turns a unique-constraint clash into `409 {"code": conflict_code}`. The
    organization is stamped after validation, so `(organization, name)`
    collisions only surface at the database — caught here instead of
    becoming a 500.
    """

    conflict_code = "CONFLICT"
    conflict_message = "A record with those values already exists"

    def _conflict_response(self):
        return Response(
            {"code": self.conflict_code, "message": self.conflict_message},
            status=status.HTTP_409_CONFLICT,
        )

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return self._conflict_response()

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except IntegrityError:
            return self._conflict_response()

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.services import password_policy_failures
from common.decorators import audit_action, required_perms
from common.tenancy import get_profile
from common.viewsets import SecureViewSet

from ..services import session_payload


class MeViewSet(SecureViewSet):
    """
    `me/` — the signed-in person's own account. No permission beyond being
    signed in: anyone may read and change what is theirs (name, password).
    Email, roles and permissions are an administrator's job.

        GET   me/            the session payload (same shape as login)
        PATCH me/profile/    first_name, last_name
        POST  me/password/   current_password, new_password
    """

    @required_perms("None")
    def list(self, request):
        get_profile(request)
        return Response(session_payload(request.user))

    @audit_action
    @required_perms("None")
    @transaction.atomic
    @action(detail=False, methods=["patch"], url_path="profile")
    def profile(self, request):
        get_profile(request)
        first_name = (request.data.get("first_name") or "").strip()
        last_name = (request.data.get("last_name") or "").strip()
        if not first_name or not last_name:
            return Response(
                {"code": "MISSING_FIELDS", "message": "first_name and last_name are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        django_user = request.user
        django_user.first_name = first_name
        django_user.last_name = last_name
        django_user.save(update_fields=["first_name", "last_name"])
        return Response(session_payload(django_user))

    @audit_action
    @required_perms("None")
    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="password")
    def password(self, request):
        """
        The current password is required whenever the account has one: a
        hijacked session must not be enough to take the account over.
        """
        django_user = request.user
        current_password = request.data.get("current_password") or ""
        new_password = request.data.get("new_password") or ""

        if django_user.has_usable_password():
            if not django_user.check_password(current_password):
                return Response(
                    {"code": "INVALID_PASSWORD", "message": "The current password is incorrect"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if current_password == new_password:
                return Response(
                    {"code": "SAME_PASSWORD", "message": "The new password must differ from the current one"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        failures = password_policy_failures(new_password, django_user)
        if failures:
            return Response(
                {"code": "WEAK_PASSWORD", "message": "The password does not meet the policy", "detail": failures},
                status=status.HTTP_400_BAD_REQUEST,
            )

        django_user.set_password(new_password)
        django_user.must_change_password = False
        django_user.save()
        return Response({"code": "PASSWORD_CHANGED", "message": "Password updated"})

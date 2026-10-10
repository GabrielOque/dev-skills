"""
Public authentication endpoints, all under `/api/auth/`:

    POST login/                     email + password            -> session
    POST refresh/                   refresh token               -> session (rotated)
    POST activation/verify/         code                        -> who the link is for
    POST activation/confirm/        code, names, password       -> session
    POST password-reset/request/    email                       -> always the same answer
    POST password-reset/verify/     code                        -> who the link is for
    POST password-reset/confirm/    code, password              -> session

A "session" is `{"access", "refresh", "user", "organization"}`.
"""

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.models import DjangoUser, ValidationCode
from accounts.services import (
    normalize_email,
    password_policy_failures,
    resolve_validation_code,
    send_password_reset_email,
)

from .serializers import (
    ActivationConfirmSerializer,
    CodeSerializer,
    EmailSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    RefreshSerializer,
)
from .services import issue_session, validate_login_user

Purpose = ValidationCode.Purpose


def _code_error(error_code):
    messages = {
        "MISSING_CODE": "The code is required",
        "INVALID_CODE": "The code is invalid",
        "EXPIRED_CODE": "The code has expired",
    }
    return Response({"code": error_code, "message": messages[error_code]}, status=status.HTTP_400_BAD_REQUEST)


def _weak_password(failures):
    return Response(
        {"code": "WEAK_PASSWORD", "message": "The password does not meet the policy", "detail": failures},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _code_owner(django_user):
    return {
        "code": "VALID_CODE",
        "message": "The code is valid",
        "email": django_user.email,
        "first_name": django_user.first_name,
        "last_name": django_user.last_name,
    }


class PublicAuthViewSet(ViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RefreshView(TokenRefreshView):
    serializer_class = RefreshSerializer


class ActivationViewSet(PublicAuthViewSet):
    """The invitation link: `{FRONTEND_URL}/activate-account/{code}`."""

    @action(detail=False, methods=["post"])
    def verify(self, request):
        payload = CodeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        validation, error = resolve_validation_code(payload.validated_data["code"], Purpose.ACTIVATION)
        if error:
            return _code_error(error)
        if validation.django_user.is_active:
            return Response(
                {"code": "ALREADY_ACTIVATED", "message": "The account is already activated"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(_code_owner(validation.django_user))

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def confirm(self, request):
        payload = ActivationConfirmSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        validation, error = resolve_validation_code(data["code"], Purpose.ACTIVATION)
        if error:
            return _code_error(error)
        django_user = validation.django_user
        if django_user.is_active:
            return Response(
                {"code": "ALREADY_ACTIVATED", "message": "The account is already activated"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        failures = password_policy_failures(data["password"], django_user)
        if failures:
            return _weak_password(failures)

        django_user.first_name = data["first_name"].strip()
        django_user.last_name = data["last_name"].strip()
        django_user.is_active = True
        django_user.must_change_password = False
        django_user.set_password(data["password"])
        django_user.save()
        validation.delete()

        validate_login_user(django_user)
        return Response(issue_session(django_user))


class PasswordResetViewSet(PublicAuthViewSet):
    """The forgot-password flow: `{FRONTEND_URL}/reset-password/{code}`.
    Also where a forced password change (`PASSWORD_CHANGE_REQUIRED`) lands."""

    # Not named `request`: that would shadow the view's `self.request`.
    @action(detail=False, methods=["post"], url_path="request")
    def request_reset(self, request):
        """
        Same answer whether or not the email exists, so this endpoint cannot
        be used to discover which accounts are registered.
        """
        payload = EmailSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        email = normalize_email(payload.validated_data["email"])

        django_user = DjangoUser.objects.select_related("profile__organization").filter(username=email).first()
        profile = getattr(django_user, "profile", None) if django_user else None
        if (
            django_user is not None
            and django_user.is_active
            and profile is not None
            and not profile.archived
            and not profile.organization.archived
        ):
            send_password_reset_email(django_user)

        return Response(
            {
                "code": "PASSWORD_RESET_REQUESTED",
                "message": "If the email is registered, a reset link was sent",
            }
        )

    @action(detail=False, methods=["post"])
    def verify(self, request):
        payload = CodeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        validation, error = resolve_validation_code(payload.validated_data["code"], Purpose.PASSWORD_RESET)
        if error:
            return _code_error(error)
        if not validation.django_user.is_active:
            return Response(
                {"code": "INACTIVE_USER", "message": "The account is not active"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(_code_owner(validation.django_user))

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def confirm(self, request):
        payload = PasswordResetConfirmSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        validation, error = resolve_validation_code(data["code"], Purpose.PASSWORD_RESET)
        if error:
            return _code_error(error)
        django_user = validation.django_user
        # Before touching the password: a deactivated account gets nothing.
        validate_login_user(django_user)

        failures = password_policy_failures(data["password"], django_user)
        if failures:
            return _weak_password(failures)

        django_user.set_password(data["password"])
        django_user.must_change_password = False
        django_user.save()
        validation.delete()

        return Response(issue_session(django_user))

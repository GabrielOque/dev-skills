from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings

from accounts.services import normalize_email
from users.services import session_payload

from .services import validate_login_user

DjangoUser = get_user_model()

INVALID_CREDENTIALS = {"code": "INVALID_CREDENTIALS", "message": "Email or password is incorrect"}


class LoginSerializer(TokenObtainPairSerializer):
    """
    Password login. People type their email; the backend authenticates on
    `username`, which always holds the normalized email.
    """

    def validate(self, attrs):
        attrs[self.username_field] = normalize_email(attrs.get(self.username_field))
        try:
            data = super().validate(attrs)
        except AuthenticationFailed as error:
            raise AuthenticationFailed(INVALID_CREDENTIALS) from error

        django_user = validate_login_user(self.user, enforce_password_change=True)
        return {**data, **session_payload(django_user)}


class RefreshSerializer(TokenRefreshSerializer):
    """
    Exchanges a refresh token for a new access token **and re-validates the
    account**: a deactivated user or organization loses the session at the
    next refresh, at most one access-token lifetime later.

    Rotates the refresh token (ROTATE_REFRESH_TOKENS) without the blacklist
    app, and returns the session payload too, so every refresh also refreshes
    the profile and permissions the frontend persisted.
    """

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])

        django_user = (
            DjangoUser.objects.select_related("profile__organization")
            .filter(id=refresh.payload.get(api_settings.USER_ID_CLAIM))
            .first()
        )
        if django_user is None:
            raise AuthenticationFailed({"code": "USER_NOT_FOUND", "message": "User not found"})
        validate_login_user(django_user)

        data = {"access": str(refresh.access_token)}
        if api_settings.ROTATE_REFRESH_TOKENS:
            refresh.set_jti()
            refresh.set_exp()
            if hasattr(refresh, "set_iat"):
                refresh.set_iat()
            data["refresh"] = str(refresh)
        return {**data, **session_payload(django_user)}


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=128)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(CodeSerializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class ActivationConfirmSerializer(CodeSerializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)

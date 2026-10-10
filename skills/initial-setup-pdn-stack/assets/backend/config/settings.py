"""
Django settings for {{PROJECT_NAME}}.

Every value that differs between environments comes from an environment
variable: locally from `.env` (copy `.env.example`), on a deployed
environment from the hosting platform. Nothing environment-specific is
hardcoded here, and every variable read below is documented in
`.env.example`.

`ENV` names the environment. It only switches infrastructure concerns
(HTTPS-only cookies, static files storage, safe local defaults), never
business behaviour:

    local        a developer machine
    test         the shared staging environment
    production   the live environment
"""

import os
from datetime import timedelta
from pathlib import Path

from corsheaders.defaults import default_headers as cors_default_headers
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Variables already present in the process environment win over `.env`, so a
# value injected by the platform can never be shadowed by a stray local file.
load_dotenv(BASE_DIR / ".env", override=False)


# An empty variable counts as unset: `.env.example` lists every key, and a
# key left blank must fall back to its default, not to "".
def env(name, default=None):
    value = os.environ.get(name)
    return default if value is None or value.strip() == "" else value.strip()


def env_bool(name, default=False):
    value = env(name)
    return default if value is None else value.lower() in ("1", "true", "yes", "on")


def env_int(name, default):
    value = env(name)
    return default if value is None else int(value)


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
PROJECT_NAME = env("PROJECT_NAME", "{{PROJECT_NAME}}")
ENV = env("ENV", "local")
IS_LOCAL = ENV == "local"
DEBUG = env_bool("DEBUG", default=False)

SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    if not IS_LOCAL:
        raise ImproperlyConfigured("SECRET_KEY must be set outside the local environment.")
    SECRET_KEY = "django-insecure-local-only-key-never-use-it-anywhere-else"

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Where the frontend lives. Used to build the links inside transactional
# emails (account activation, password reset).
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:3000").rstrip("/")


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", ",".join(CORS_ALLOWED_ORIGINS))

# django-cors-headers only allows its default request headers on preflight.
# `X-Latitude` / `X-Longitude` let the frontend send where a mutation came
# from; `common.decorators.audit_action` stores them.
CORS_ALLOW_HEADERS = (*cors_default_headers, "x-latitude", "x-longitude")
# File downloads name the file in `Content-Disposition`; the browser hides
# the header from JavaScript unless it is exposed.
CORS_EXPOSE_HEADERS = ("Content-Disposition",)

if not IS_LOCAL:
    # Hosting platforms terminate TLS at their edge and forward plain HTTP.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# ---------------------------------------------------------------------------
# Database — PostgreSQL only
# ---------------------------------------------------------------------------
# Most platforms inject a single DATABASE_URL; the discrete DB_* variables are
# the local fallback.
DATABASE_URL = env("DATABASE_URL")

if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=env_int("DB_CONN_MAX_AGE", 600),
            conn_health_checks=True,
            ssl_require=env_bool("DB_SSL_REQUIRE", default=not IS_LOCAL),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "{{PROJECT_DB}}"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
            "CONN_HEALTH_CHECKS": True,
        }
    }


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    # Stands in for "django.contrib.auth" (same app, relabelled admin section).
    "config.apps.CustomAuthConfig",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # `__unaccent` lookups and the `unaccent()` used by raw-SQL searches.
    "django.contrib.postgres",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # Project. `common` is the base layer every other app builds on.
    "common",
    "accounts",
    "organizations",
    "users",
    "authentication",
    "audit",
]

# The login identity, with a UUID primary key like every other table.
# See accounts.models.DjangoUser and users.models.User.
AUTH_USER_MODEL = "accounts.DjangoUser"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # before CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "common.middleware.TrimQueryParamsMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
# The backend speaks English (code, API messages); the frontend owns the copy
# a person reads.
LANGUAGE_CODE = env("LANGUAGE_CODE", "en-us")
TIME_ZONE = env("TIME_ZONE", "{{TIME_ZONE}}")
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# REST framework & JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": (
        ("rest_framework.renderers.JSONRenderer", "rest_framework.renderers.BrowsableAPIRenderer")
        if DEBUG
        else ("rest_framework.renderers.JSONRenderer",)
    ),
    # Every error leaves the API as {"code", "message", "detail"?}.
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
    # Public authentication endpoints opt into this scope (per client IP).
    "DEFAULT_THROTTLE_RATES": {"auth": env("AUTH_THROTTLE_RATE", "20/minute")},
    # Proxies in front of the app (load balancer = 1), so throttling reads the
    # real client IP from X-Forwarded-For. Unset = DRF's default behaviour.
    "NUM_PROXIES": env_int("NUM_PROXIES", None),
}

# The session lives as long as the refresh token. The access token is short on
# purpose; the frontend mints a new one silently before it expires. Every
# refresh rotates the refresh token, so an active user stays signed in and an
# idle one is signed out after JWT_REFRESH_TOKEN_DAYS.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_TOKEN_MINUTES", 15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_TOKEN_DAYS", 3)),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SIGNING_KEY") or SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Lifetime of the single-use links sent by email (activation, password reset).
VALIDATION_CODE_HOURS = env_int("VALIDATION_CODE_HOURS", 24)


# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Uploaded files go to an S3-compatible bucket when one is configured (AWS S3,
# Cloudflare R2, MinIO…) and to the local disk otherwise. django-storages reads
# the AWS_* settings below directly.
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")
AWS_DEFAULT_ACL = None  # rely on the bucket policy, not on object ACLs
AWS_QUERYSTRING_AUTH = True  # private files, signed URLs
AWS_QUERYSTRING_EXPIRE = env_int("AWS_QUERYSTRING_EXPIRE", 3600)

STORAGES = {
    "default": {
        "BACKEND": (
            "storages.backends.s3.S3Storage"
            if AWS_STORAGE_BUCKET_NAME
            else "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if IS_LOCAL
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
# Locally emails are printed to the console. Elsewhere any SMTP provider
# works; swap EMAIL_BACKEND for a provider backend if the project needs one.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if IS_LOCAL
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "no-reply@example.com")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}

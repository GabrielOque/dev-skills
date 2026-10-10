from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

admin.site.site_header = f"{settings.PROJECT_NAME} — administration"
admin.site.site_title = settings.PROJECT_NAME


def health(_request):
    """Liveness probe. Touches no database, so a database blip does not get
    the container restarted."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health),
    path("admin/", admin.site.urls),
    # Authentication: login, refresh, activation, password reset.
    path("api/auth/", include("authentication.urls")),
    # Application. Every app registers its own router under `api/`.
    path("api/", include("users.urls")),
    path("api/", include("organizations.urls")),
]

# Local uploads (only when no bucket is configured; `static()` is a no-op
# unless DEBUG is on).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

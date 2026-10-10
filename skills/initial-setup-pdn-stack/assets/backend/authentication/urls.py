from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ActivationViewSet, LoginView, PasswordResetViewSet, RefreshView

router = SimpleRouter()
router.register(r"activation", ActivationViewSet, basename="activation")
router.register(r"password-reset", PasswordResetViewSet, basename="password-reset")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    *router.urls,
]

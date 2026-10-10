from rest_framework.routers import SimpleRouter

from .views import MeViewSet, PermissionViewSet, RoleViewSet, UserViewSet

router = SimpleRouter()
router.register(r"me", MeViewSet, basename="me")
router.register(r"users", UserViewSet, basename="users")
router.register(r"roles", RoleViewSet, basename="roles")
router.register(r"permissions", PermissionViewSet, basename="permissions")

urlpatterns = router.urls

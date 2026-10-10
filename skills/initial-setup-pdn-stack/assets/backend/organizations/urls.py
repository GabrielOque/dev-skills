from rest_framework.routers import SimpleRouter

from .views import OrganizationViewSet

router = SimpleRouter()
router.register(r"organization", OrganizationViewSet, basename="organization")

urlpatterns = router.urls

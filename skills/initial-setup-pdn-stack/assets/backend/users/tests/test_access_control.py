from django.test import TestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from common.decorators import get_effective_permission_codenames, required_perms
from common.testing import authenticated_client, make_organization, make_permissions, make_role, make_user
from common.viewsets import SecureViewSet


class EffectivePermissionsTests(TestCase):
    def setUp(self):
        self.organization = make_organization()

    def test_union_of_active_roles_and_direct_permissions(self):
        role = make_role(self.organization, "Viewer", ["access.users.view"])
        archived = make_role(self.organization, "Old", ["access.roles.view"], archived=True)
        profile = make_user(
            self.organization,
            "union@example.com",
            permissions=["access.permissions.view"],
            roles=[role, archived],
        )

        held = get_effective_permission_codenames(profile.django_user)

        self.assertEqual(held, {"access.users.view", "access.permissions.view"})

    def test_archived_permission_grants_nothing(self):
        (permission,) = make_permissions("access.users.view")
        permission.archived = True
        permission.save()
        profile = make_user(self.organization, "archived@example.com", permissions=["access.users.view"])

        self.assertEqual(get_effective_permission_codenames(profile.django_user), set())

    def test_superuser_holds_every_active_permission(self):
        make_permissions("access.users.view", "access.roles.view")
        profile = make_user(self.organization, "root@example.com", is_superuser=True)

        held = get_effective_permission_codenames(profile.django_user)

        self.assertTrue({"access.users.view", "access.roles.view"} <= held)


class RequiredPermsTests(TestCase):
    def setUp(self):
        self.organization = make_organization()
        make_permissions("access.roles.view")

    def test_denied_without_permission_and_codenames_not_disclosed(self):
        profile = make_user(self.organization, "nobody@example.com")

        response = authenticated_client(profile).get("/api/roles/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "PERMISSION_DENIED")
        self.assertNotIn("access.roles.view", str(response.data))

    def test_allowed_with_permission(self):
        profile = make_user(self.organization, "viewer@example.com", permissions=["access.roles.view"])

        response = authenticated_client(profile).get("/api/roles/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)

    def test_disallowed_method_is_405_not_a_missing_decorator(self):
        profile = make_user(self.organization, "put@example.com", permissions=["access.roles.view"])

        response = authenticated_client(profile).put(f"/api/users/{profile.id}/", {}, format="json")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.data["code"], "METHOD_NOT_ALLOWED")

    def test_anonymous_gets_401(self):
        from rest_framework.test import APIClient

        response = APIClient().get("/api/roles/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "AUTHENTICATION_REQUIRED")

    def test_undecorated_action_is_refused(self):
        class OpenViewSet(SecureViewSet):
            def list(self, request):
                return Response({"open": True})

        class GatedViewSet(SecureViewSet):
            @required_perms("None")
            def list(self, request):
                return Response({"open": True})

        profile = make_user(self.organization, "dev@example.com")
        factory = APIRequestFactory()

        request = factory.get("/")
        force_authenticate(request, user=profile.django_user)
        response = OpenViewSet.as_view({"get": "list"})(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "MISSING_PERMS_DECORATOR")

        request = factory.get("/")
        force_authenticate(request, user=profile.django_user)
        self.assertEqual(GatedViewSet.as_view({"get": "list"})(request).status_code, 200)


class TenantIsolationTests(TestCase):
    def test_another_organizations_role_is_not_found(self):
        mine, theirs = make_organization("Mine"), make_organization("Theirs")
        foreign_role = make_role(theirs, "Foreign")
        profile = make_user(mine, "isolated@example.com", permissions=["access.roles.view", "access.roles.edit"])
        client = authenticated_client(profile)

        self.assertEqual(client.get(f"/api/roles/{foreign_role.id}/").status_code, 404)
        self.assertEqual(client.patch(f"/api/roles/{foreign_role.id}/", {"name": "x"}).status_code, 404)

    def test_user_cannot_be_given_a_foreign_role(self):
        mine, theirs = make_organization("Mine"), make_organization("Theirs")
        foreign_role = make_role(theirs, "Foreign")
        admin = make_user(mine, "admin@example.com", permissions=["access.users.create"])

        response = authenticated_client(admin).post(
            "/api/users/",
            {"email": "new@example.com", "first_name": "New", "last_name": "User", "roles": [str(foreign_role.id)]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "INVALID_ROLE")


class RoleCrudTests(TestCase):
    def setUp(self):
        self.organization = make_organization()
        make_permissions("access.users.view")
        self.client = authenticated_client(
            make_user(
                self.organization,
                "roles@example.com",
                permissions=["access.roles.view", "access.roles.create", "access.roles.deactivate"],
            )
        )

    def test_create_duplicate_name_is_409(self):
        payload = {"name": "Cashier", "permissions": ["access.users.view"]}
        self.assertEqual(self.client.post("/api/roles/", payload, format="json").status_code, 201)

        response = self.client.post("/api/roles/", payload, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "ROLE_NAME_TAKEN")

    def test_destroy_archives_and_restore_reactivates(self):
        role_id = self.client.post("/api/roles/", {"name": "Temp"}, format="json").data["id"]

        self.assertEqual(self.client.delete(f"/api/roles/{role_id}/").data["code"], "ARCHIVED")
        listing = self.client.get("/api/roles/", {"status[]": "inactive", "search": "temp"})
        self.assertEqual(listing.data["total_rows"], 1)

        self.assertFalse(self.client.patch(f"/api/roles/{role_id}/restore/").data["archived"])

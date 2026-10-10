import re

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import ValidationCode
from common.testing import DEFAULT_PASSWORD, authenticated_client, make_organization, make_user

NEW_PASSWORD = "N3w!Secret-pass"


def code_from_last_email(path):
    match = re.search(rf"/{path}/([\w-]+)", mail.outbox[-1].body)
    return match.group(1)


class LoginAndRefreshTests(TestCase):
    def setUp(self):
        cache.clear()  # throttling counters
        self.client = APIClient()
        self.organization = make_organization()
        self.profile = make_user(self.organization, "ana@example.com", permissions=["access.users.view"])

    def login(self, email="ana@example.com", password=DEFAULT_PASSWORD):
        return self.client.post("/api/auth/login/", {"username": email, "password": password}, format="json")

    def test_login_normalizes_the_email_and_returns_the_session(self):
        response = self.login(email="  ANA@Example.com ")

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["permissions"], ["access.users.view"])
        self.assertEqual(response.data["organization"]["id"], self.organization.id)

    def test_wrong_password_is_invalid_credentials(self):
        response = self.login(password="nope")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "INVALID_CREDENTIALS")

    def test_refresh_rotates_and_revalidates_the_account(self):
        refresh = self.login().data["refresh"]

        response = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data["refresh"], refresh)
        self.assertIn("user", response.data)

        self.profile.archived = True
        self.profile.save()
        response = self.client.post("/api/auth/refresh/", {"refresh": response.data["refresh"]}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "USER_OR_ORGANIZATION_ARCHIVED")

    def test_garbage_refresh_token_is_token_invalid(self):
        response = self.client.post("/api/auth/refresh/", {"refresh": "not-a-token"}, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "TOKEN_INVALID")

    def test_temporary_password_withholds_the_session(self):
        django_user = self.profile.django_user
        django_user.must_change_password = True
        django_user.save()

        response = self.login()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "PASSWORD_CHANGE_REQUIRED")
        self.assertNotIn("access", response.data)

        confirm = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"code": response.data["reset_code"], "password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(confirm.status_code, 200)
        self.assertIn("access", confirm.data)
        django_user.refresh_from_db()
        self.assertFalse(django_user.must_change_password)


class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.profile = make_user(make_organization(), "reset@example.com")

    def test_request_answers_the_same_for_unknown_emails(self):
        known = self.client.post("/api/auth/password-reset/request/", {"email": "reset@example.com"}, format="json")
        unknown = self.client.post("/api/auth/password-reset/request/", {"email": "ghost@example.com"}, format="json")

        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_full_flow_and_single_use(self):
        self.client.post("/api/auth/password-reset/request/", {"email": "reset@example.com"}, format="json")
        code = code_from_last_email("reset-password")

        verify = self.client.post("/api/auth/password-reset/verify/", {"code": code}, format="json")
        self.assertEqual(verify.data["email"], "reset@example.com")

        weak = self.client.post("/api/auth/password-reset/confirm/", {"code": code, "password": "weak"}, format="json")
        self.assertEqual(weak.data["code"], "WEAK_PASSWORD")

        confirm = self.client.post(
            "/api/auth/password-reset/confirm/", {"code": code, "password": NEW_PASSWORD}, format="json"
        )
        self.assertEqual(confirm.status_code, 200)
        self.assertIn("access", confirm.data)

        reused = self.client.post(
            "/api/auth/password-reset/confirm/", {"code": code, "password": NEW_PASSWORD}, format="json"
        )
        self.assertEqual(reused.data["code"], "INVALID_CODE")

    def test_a_code_only_works_for_its_own_purpose(self):
        self.client.post("/api/auth/password-reset/request/", {"email": "reset@example.com"}, format="json")
        code = code_from_last_email("reset-password")

        response = self.client.post("/api/auth/activation/verify/", {"code": code}, format="json")

        self.assertEqual(response.data["code"], "INVALID_CODE")


class InvitationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.organization = make_organization()
        self.admin = make_user(self.organization, "admin@example.com", permissions=["access.users.create"])

    def test_invite_then_activate_signs_the_user_in(self):
        created = authenticated_client(self.admin).post(
            "/api/users/",
            {"email": "New.Person@Example.com", "first_name": "New", "last_name": "Person"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["status"], "pending")
        self.assertTrue(created.data["invitation_sent"])

        code = code_from_last_email("activate-account")
        client = APIClient()
        self.assertEqual(client.post("/api/auth/activation/verify/", {"code": code}, format="json").status_code, 200)

        confirm = client.post(
            "/api/auth/activation/confirm/",
            {"code": code, "first_name": "Nueva", "last_name": "Persona", "password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(confirm.status_code, 200)
        self.assertEqual(confirm.data["user"]["email"], "new.person@example.com")
        self.assertFalse(ValidationCode.objects.filter(code=code).exists())

    def test_duplicate_email_is_409(self):
        client = authenticated_client(self.admin)
        payload = {"email": "admin@example.com", "first_name": "A", "last_name": "B"}

        response = client.post("/api/users/", payload, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "EMAIL_TAKEN")

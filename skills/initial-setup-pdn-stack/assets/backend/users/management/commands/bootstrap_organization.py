"""
Create the first organization, an administrator role holding every
permission, and its owner — the account that then creates everyone else
from the application. Idempotent: running it again updates the same rows.

    python manage.py bootstrap_organization \
        --organization "Acme" --email owner@acme.com \
        --first-name Ana --last-name Pérez

Without `--password` a temporary password is generated and printed; the
owner must replace it at the first sign-in (`must_change_password`).
`--superuser` also makes the owner a Django superuser (admin site access,
bypasses every permission check) — reserve it for the platform operator.
"""

import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.services import normalize_email
from organizations.models import Organization
from users.models import Permission, Role, User

DjangoUser = get_user_model()


class Command(BaseCommand):
    help = "Create (or update) an organization, its administrator role and its owner."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True, help="Organization name")
        parser.add_argument("--email", required=True, help="Owner email (it is the login)")
        parser.add_argument("--first-name", required=True)
        parser.add_argument("--last-name", required=True)
        parser.add_argument("--password", help="Owner password. Omit to generate a temporary one.")
        parser.add_argument("--role-name", default="Administrator", help="Name of the all-permissions role")
        parser.add_argument("--superuser", action="store_true", help="Also grant Django superuser/staff")

    @transaction.atomic
    def handle(self, *args, **options):
        permissions = list(Permission.objects.filter(archived=False))
        if not permissions:
            raise CommandError("The permission catalogue is empty: run `python manage.py sync_permissions` first.")

        organization, _ = Organization.objects.get_or_create(name=options["organization"].strip())

        role, _ = Role.objects.get_or_create(
            organization=organization,
            name=options["role_name"].strip(),
            defaults={"description": "Every permission of the application."},
        )
        role.archived = False
        role.save(update_fields=["archived", "updated_at"])
        role.permissions.set(permissions)

        email = normalize_email(options["email"])
        existing = DjangoUser.objects.filter(username=email).first()
        django_user = existing or DjangoUser(username=email)
        django_user.email = email
        django_user.first_name = options["first_name"].strip()
        django_user.last_name = options["last_name"].strip()
        django_user.is_active = True
        django_user.is_staff = django_user.is_superuser = options["superuser"]

        temporary = None
        if options["password"]:
            django_user.set_password(options["password"])
            django_user.must_change_password = False
        elif existing is None or not existing.has_usable_password():
            temporary = secrets.token_urlsafe(12)
            django_user.set_password(temporary)
            django_user.must_change_password = True
        django_user.save()

        profile, _ = User.objects.get_or_create(django_user=django_user, defaults={"organization": organization})
        if profile.organization_id != organization.id:
            raise CommandError(f"{email} already belongs to another organization ({profile.organization}).")
        profile.archived = False
        profile.save(update_fields=["archived", "updated_at"])
        profile.roles.add(role)

        self.stdout.write(self.style.SUCCESS(f"Organization: {organization.name} ({organization.slug})"))
        self.stdout.write(f"Role: {role.name} — {len(permissions)} permissions")
        self.stdout.write(f"Owner: {email}{' (superuser)' if options['superuser'] else ''}")
        if temporary:
            self.stdout.write(self.style.WARNING(f"Temporary password: {temporary}  (must be changed at first sign-in)"))

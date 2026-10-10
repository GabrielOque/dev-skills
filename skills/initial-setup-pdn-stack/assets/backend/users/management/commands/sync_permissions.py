"""
Make the `permission` table hold exactly the catalogue — nothing more.

The fixture `users/fixtures/permissions_catalog.json` is the only source of
truth. This command:

1. validates it (codename shape, duplicates, deterministic uuid5 pks);
2. upserts every row with `loaddata` (idempotent: same pk, same row);
3. moves role and user assignments from renamed codenames (`RENAMES`) to
   their replacements — a rename is a new row, so without this every role
   would silently lose the permission;
4. deletes every permission whose codename is not in the fixture
   (`--keep-unknown` skips this step).

Run it on every deploy, after `migrate`:

    python manage.py sync_permissions --dry-run   # prints, writes nothing
    python manage.py sync_permissions

Idempotent: a second run changes nothing.
"""

import json
import re
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from users.models import Permission, Role, User, permission_pk

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "permissions_catalog.json"
CODENAME = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,3}$")

# Old codename -> the codenames that replace it. Keep entries until every
# environment has run the command once after the rename.
RENAMES = {
    # "billing.invoices.cancel": ["billing.invoices.void"],
}


def load_catalogue():
    try:
        rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CommandError(f"Cannot read {FIXTURE}: {error}") from error

    problems, catalogue = [], {}
    for index, row in enumerate(rows):
        if row.get("model") != "users.permission":
            problems.append(f"[{index}] unexpected model {row.get('model')!r}")
            continue
        name = row.get("fields", {}).get("name", "")
        if not CODENAME.match(name):
            problems.append(f"[{index}] invalid codename {name!r} (expected module.resource.action)")
        if name in catalogue:
            problems.append(f"[{index}] duplicated codename {name}")
        if row.get("pk") != str(permission_pk(name)):
            problems.append(f"[{index}] {name}: pk must be {permission_pk(name)}")
        catalogue[name] = row.get("fields", {}).get("description", "")
    if problems:
        raise CommandError("Invalid permission catalogue:\n  " + "\n  ".join(problems))
    return catalogue


class Command(BaseCommand):
    help = "Apply users/fixtures/permissions_catalog.json: upsert, apply renames, prune unknown codenames."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Print what would change and write nothing.")
        parser.add_argument(
            "--keep-unknown",
            action="store_true",
            help="Do not delete permissions that are missing from the fixture.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        catalogue = load_catalogue()

        broken = {target for targets in RENAMES.values() for target in targets} - set(catalogue)
        if broken:
            raise CommandError(f"RENAMES points at codenames missing from the fixture: {sorted(broken)}")

        existing = dict(Permission.objects.values_list("name", "description"))
        added = sorted(set(catalogue) - set(existing))
        changed = sorted(name for name in set(catalogue) & set(existing) if catalogue[name] != existing[name])
        stale = sorted(set(existing) - set(catalogue))

        self.stdout.write(f"Catalogue: {len(catalogue)} permissions")
        self._report("New", added)
        self._report("Description changed", changed)
        self._report("Renamed (assignments move)", [f"{old} -> {RENAMES[old]}" for old in stale if old in RENAMES])
        self._report("Not in the fixture (deleted)" if not options["keep_unknown"] else "Not in the fixture (kept)", stale)

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: nothing was written."))
            return

        with transaction.atomic():
            call_command("loaddata", str(FIXTURE), verbosity=0)
            self._apply_renames()
            if stale and not options["keep_unknown"]:
                Permission.objects.filter(name__in=stale).delete()

        self.stdout.write(self.style.SUCCESS("Permissions in sync."))

    def _apply_renames(self):
        for old, targets in RENAMES.items():
            source = Permission.objects.filter(name=old).first()
            if source is None:
                continue
            replacements = list(Permission.objects.filter(name__in=targets))
            for role in Role.objects.filter(permissions=source):
                role.permissions.add(*replacements)
            for profile in User.objects.filter(permissions=source):
                profile.permissions.add(*replacements)

    def _report(self, label, items):
        if items:
            self.stdout.write(f"  {label}: {len(items)}")
            for item in items:
                self.stdout.write(f"    - {item}")

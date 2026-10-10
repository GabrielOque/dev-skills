"""
Developer tool: append codenames to the permission catalogue fixture with
their deterministic pk, so nobody computes uuid5 by hand.

    python manage.py add_permission billing.invoices.view "Ver facturas" \
                                    billing.invoices.void "Anular facturas"

It edits `users/fixtures/permissions_catalog.json` (commit the change) and
writes nothing to the database: apply it with `sync_permissions`.
"""

import json
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from users.models import permission_pk

from .sync_permissions import CODENAME, FIXTURE


class Command(BaseCommand):
    help = "Append codename/description pairs to the permission catalogue fixture."

    def add_arguments(self, parser):
        parser.add_argument("pairs", nargs="+", help="codename description [codename description ...]")

    def handle(self, *args, **options):
        pairs = options["pairs"]
        if len(pairs) % 2:
            raise CommandError("Arguments come in pairs: codename description")

        rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
        present = {row["fields"]["name"] for row in rows}
        stamp = f"{date.today().isoformat()}T00:00:00Z"

        added = 0
        for codename, description in zip(pairs[::2], pairs[1::2]):
            if not CODENAME.match(codename):
                raise CommandError(f"'{codename}' is not module.resource.action in lowercase snake_case")
            if codename in present:
                self.stdout.write(f"  = {codename} (already in the catalogue)")
                continue
            rows.append(
                {
                    "model": "users.permission",
                    "pk": str(permission_pk(codename)),
                    "fields": {
                        "name": codename,
                        "description": description.strip(),
                        "archived": False,
                        "created_at": stamp,
                        "updated_at": stamp,
                    },
                }
            )
            present.add(codename)
            added += 1
            self.stdout.write(f"  + {codename}")

        FIXTURE.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        self.stdout.write(self.style.SUCCESS(f"{added} permission(s) added. Run `sync_permissions` to apply."))

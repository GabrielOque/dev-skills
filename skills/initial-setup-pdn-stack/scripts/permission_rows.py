#!/usr/bin/env python3
"""
Build or check rows of the permission catalogue fixture
(`users/fixtures/permissions_catalog.json` in the generated backend).

Every row's pk is uuid5 of its codename — the same function the backend uses
(`users.models.permission.permission_pk`) — so the fixture is deterministic
and `loaddata` is idempotent. Never invent pks by hand: use this script.

Usage:
    # Print new rows (paste them into the fixture, or use --append)
    python permission_rows.py "billing.invoices.view=Ver facturas" "billing.invoices.void=Anular facturas"

    # Append new rows to a fixture in place (skips codenames already present)
    python permission_rows.py --append path/to/permissions_catalog.json "billing.invoices.view=Ver facturas"

    # Validate a fixture: codename shape, duplicates, deterministic pks
    python permission_rows.py --check path/to/permissions_catalog.json

Standard library only.
"""

import argparse
import json
import re
import sys
import uuid
from datetime import date
from pathlib import Path

# Must match users/models/permission.py in the generated backend.
PERMISSION_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "urn:pdn:permission")
MODEL = "users.permission"
# <module>.<resource>.<action> (2 to 4 lowercase snake_case segments).
CODENAME = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,3}$")


def permission_pk(codename):
    return str(uuid.uuid5(PERMISSION_NAMESPACE, codename))


def build_row(codename, description, stamp):
    return {
        "model": MODEL,
        "pk": permission_pk(codename),
        "fields": {
            "name": codename,
            "description": description,
            "archived": False,
            "created_at": stamp,
            "updated_at": stamp,
        },
    }


def parse_spec(spec):
    if "=" not in spec:
        raise ValueError(f"'{spec}' must look like codename=Description")
    codename, description = (part.strip() for part in spec.split("=", 1))
    if not CODENAME.match(codename):
        raise ValueError(f"'{codename}' is not <module>.<resource>.<action> in lowercase snake_case")
    if not description:
        raise ValueError(f"'{codename}' needs a description")
    return codename, description


def check(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    problems, seen = [], set()
    for index, row in enumerate(rows):
        if row.get("model") != MODEL:
            continue
        name = row.get("fields", {}).get("name", "")
        if not CODENAME.match(name):
            problems.append(f"[{index}] invalid codename: {name!r}")
        if name in seen:
            problems.append(f"[{index}] duplicated codename: {name}")
        seen.add(name)
        expected = permission_pk(name)
        if row.get("pk") != expected:
            problems.append(f"[{index}] {name}: pk should be {expected}")
        if not row.get("fields", {}).get("description"):
            problems.append(f"[{index}] {name}: missing description")
    return problems, len(seen)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("specs", nargs="*", help='"codename=Description" pairs')
    parser.add_argument("--check", metavar="FIXTURE", help="validate an existing fixture")
    parser.add_argument("--append", metavar="FIXTURE", help="append the new rows to this fixture")
    parser.add_argument("--date", default=date.today().isoformat(), help="timestamp date (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.check:
        problems, total = check(args.check)
        for problem in problems:
            print(problem, file=sys.stderr)
        print(f"{total} permissions checked, {len(problems)} problem(s).")
        return 1 if problems else 0

    if not args.specs:
        parser.error("give at least one codename=Description pair, or --check")

    stamp = f"{args.date}T00:00:00Z"
    try:
        rows = [build_row(*parse_spec(spec), stamp) for spec in args.specs]
    except ValueError as error:
        parser.error(str(error))

    if args.append:
        path = Path(args.append)
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        present = {row.get("fields", {}).get("name") for row in existing}
        added = [row for row in rows if row["fields"]["name"] not in present]
        path.write_text(json.dumps(existing + added, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"Appended {len(added)} row(s) to {path} ({len(rows) - len(added)} already present).")
        return 0

    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Create a new skill from `template/` and register it in the catalog.

    python scripts/new_skill.py <skill-name> \
        --summary "Una línea: qué hace la skill" \
        --description "What it does and when to use it (third person, with trigger phrases)" \
        [--category development] [--tags "django,api"]

Creates skills/<skill-name>/{SKILL.md, README.md, CHANGELOG.md}, then runs
sync_catalog.py so the marketplace and the README catalog list it. Fill the
TODOs, add references/ scripts/ assets/ as needed, and run
`python scripts/validate_skills.py`.
"""

import argparse
import sys
from datetime import date

from skills_lib import CATEGORIES, NAME_PATTERN, SKILLS_DIR, TEMPLATE_DIR
from sync_catalog import main as sync_catalog

TEMPLATES = {
    "SKILL.template.md": "SKILL.md",
    "README.template.md": "README.md",
    "CHANGELOG.template.md": "CHANGELOG.md",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="kebab-case, matches the directory: e.g. django-module-crud")
    parser.add_argument("--summary", required=True, help="one line for the catalog and the plugin listing")
    parser.add_argument("--description", required=True, help="what it does + when to use it (<= 1024 chars)")
    parser.add_argument("--category", default="development", choices=CATEGORIES)
    parser.add_argument("--tags", default="", help="comma-separated")
    args = parser.parse_args()

    if not NAME_PATTERN.match(args.name) or len(args.name) > 64:
        parser.error("name must be 1-64 chars of a-z, 0-9 and single hyphens")
    if len(args.description) > 1024:
        parser.error("description must be <= 1024 chars")

    target = SKILLS_DIR / args.name
    if target.exists():
        parser.error(f"{target} already exists")

    values = {
        "{{NAME}}": args.name,
        "{{TITLE}}": args.name.replace("-", " ").capitalize(),
        "{{SUMMARY}}": args.summary.strip(),
        "{{DESCRIPTION}}": args.description.strip(),
        "{{CATEGORY}}": args.category,
        "{{TAGS}}": ",".join(tag.strip() for tag in args.tags.split(",") if tag.strip()),
        "{{DATE}}": date.today().isoformat(),
    }

    target.mkdir(parents=True)
    for source_name, target_name in TEMPLATES.items():
        text = (TEMPLATE_DIR / source_name).read_text(encoding="utf-8")
        for token, value in values.items():
            text = text.replace(token, value)
        (target / target_name).write_text(text, encoding="utf-8", newline="\n")
        print(f"created skills/{args.name}/{target_name}")

    sys.argv = [sys.argv[0]]
    sync_catalog()
    print(
        "\nNext: fill the TODOs in SKILL.md and README.md, add references/ scripts/ assets/ "
        "as needed, then run `python scripts/validate_skills.py`."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

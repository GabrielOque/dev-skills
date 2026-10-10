#!/usr/bin/env python3
"""
Regenerate the plugin entries of `.claude-plugin/marketplace.json` and the
catalog table of `README.md` from the skills' frontmatter.

    python scripts/sync_catalog.py          # write
    python scripts/sync_catalog.py --check  # exit 1 if anything is out of date (CI)

Each skill becomes one installable plugin (`/plugin install <skill>@<marketplace>`).
Edit SKILL.md frontmatter, never the generated parts by hand.
"""

import argparse
import sys

from skills_lib import (
    MARKETPLACE,
    README,
    catalog_table,
    load_marketplace,
    load_skill,
    plugin_entry,
    replace_catalog,
    skill_dirs,
    write_json,
)


def build():
    skills = [load_skill(path) for path in skill_dirs()]
    marketplace = load_marketplace()
    marketplace["plugins"] = [plugin_entry(skill) for skill in skills]
    readme = replace_catalog(README.read_text(encoding="utf-8"), catalog_table(skills))
    return marketplace, readme


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only verify, write nothing")
    args = parser.parse_args()

    marketplace, readme = build()
    current_marketplace = load_marketplace()
    current_readme = README.read_text(encoding="utf-8")

    stale = []
    if marketplace != current_marketplace:
        stale.append(str(MARKETPLACE.relative_to(MARKETPLACE.parents[1])))
    if readme != current_readme:
        stale.append("README.md")

    if args.check:
        if stale:
            print("Out of date: " + ", ".join(stale) + " — run `python scripts/sync_catalog.py`.", file=sys.stderr)
            return 1
        print("Catalog in sync.")
        return 0

    write_json(MARKETPLACE, marketplace)
    README.write_text(readme, encoding="utf-8", newline="\n")
    print("Updated: " + (", ".join(stale) if stale else "nothing (already in sync)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

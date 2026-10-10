#!/usr/bin/env python3
"""
Bump a skill's version (semver) and open its CHANGELOG entry.

    python scripts/bump_version.py <skill-name> patch|minor|major
    python scripts/bump_version.py <skill-name> 2.0.0

Updates `metadata.version` in SKILL.md, adds `## [X.Y.Z] - YYYY-MM-DD` to the
skill's CHANGELOG.md (moving the "Unreleased" notes under it), and syncs the
catalog. Then tag the release: `git tag <skill-name>@X.Y.Z`.

  patch  fixes and wording that don't change what the skill produces
  minor  new capabilities, backwards compatible
  major  changes to what the skill generates or expects (breaking)
"""

import re
import sys
from datetime import date

from skills_lib import SEMVER_PATTERN, SKILLS_DIR, load_skill
from sync_catalog import main as sync_catalog


def next_version(current, part):
    if SEMVER_PATTERN.match(part):
        return part
    major, minor, patch = (int(number) for number in current.split("-")[0].split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    sys.exit("error: second argument must be patch, minor, major or an explicit X.Y.Z")


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    name, part = argv
    path = SKILLS_DIR / name
    if not (path / "SKILL.md").exists():
        sys.exit(f"error: skills/{name}/SKILL.md not found")

    current = load_skill(path)["frontmatter"].get("metadata", {}).get("version", "0.0.0")
    new = next_version(current, part)

    skill_md = path / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    text, count = re.subn(r'(\n\s+version:\s*)"?[^"\n]+"?', rf'\g<1>"{new}"', text, count=1)
    if not count:
        sys.exit("error: metadata.version not found in SKILL.md")
    skill_md.write_text(text, encoding="utf-8", newline="\n")

    changelog = path / "CHANGELOG.md"
    log = changelog.read_text(encoding="utf-8")
    heading = f"## [{new}] - {date.today().isoformat()}"
    if "## [Unreleased]" in log:
        log = log.replace("## [Unreleased]", f"## [Unreleased]\n\n{heading}", 1)
    else:
        log = re.sub(r"(\n## \[)", f"\n{heading}\n\n- TODO: describe the changes.\n\\1", log, count=1)
    changelog.write_text(log, encoding="utf-8", newline="\n")

    sys.argv = [sys.argv[0]]
    sync_catalog()
    print(f"{name}: {current} -> {new}. Review CHANGELOG.md, commit, then `git tag {name}@{new}`.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

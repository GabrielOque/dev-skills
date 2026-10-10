#!/usr/bin/env python3
"""
Validate every skill in `skills/` against the Agent Skills specification and
this repository's conventions (docs/AUTHORING.md). Run it before every
commit; CI runs it on every push.

    python scripts/validate_skills.py            # all skills
    python scripts/validate_skills.py <name> …   # only these

Exit code 1 when any error is found. Warnings never fail the run.
"""

import re
import sys

from skills_lib import (
    CATEGORIES,
    NAME_PATTERN,
    README,
    SEMVER_PATTERN,
    SKILLS_DIR,
    FrontmatterError,
    load_marketplace,
    load_skill,
    skill_dirs,
)
from sync_catalog import build as build_catalog

SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
CLAUDE_CODE_KEYS = {
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "background",
    "hooks",
    "paths",
    "shell",
}
REQUIRED_METADATA = ("version", "summary", "category")
RESERVED_WORDS = ("anthropic", "claude")
MAX_SKILL_LINES = 500
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
XML_TAG = re.compile(r"<[A-Za-z/][^>]*>")


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, where, message):
        self.errors.append(f"ERROR   {where}: {message}")

    def warn(self, where, message):
        self.warnings.append(f"WARNING {where}: {message}")


def check_links(report, where, base, text):
    for target in MARKDOWN_LINK.findall(text):
        if re.match(r"^[a-z]+:", target):  # http:, https:, mailto:
            continue
        if not (base / target).exists():
            report.error(where, f"broken link -> {target}")


def check_skill(report, path):
    where = f"skills/{path.name}"
    if not (path / "SKILL.md").exists():
        report.error(where, "missing SKILL.md")
        return
    try:
        skill = load_skill(path)
    except FrontmatterError as error:
        report.error(where, f"frontmatter: {error}")
        return

    frontmatter = skill["frontmatter"]
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    metadata = frontmatter.get("metadata", {})

    # --- Agent Skills spec -------------------------------------------------
    if not name:
        report.error(where, "frontmatter 'name' is required")
    else:
        if not NAME_PATTERN.match(name) or len(name) > 64:
            report.error(where, f"name '{name}' must be 1-64 chars of a-z, 0-9 and single hyphens")
        if name != path.name:
            report.error(where, f"name '{name}' must match the directory name '{path.name}'")
        if any(word in name for word in RESERVED_WORDS):
            report.error(where, f"name '{name}' must not contain {RESERVED_WORDS}")
    if not description:
        report.error(where, "frontmatter 'description' is required")
    elif len(description) > 1024:
        report.error(where, f"description is {len(description)} chars (max 1024)")
    elif XML_TAG.search(description):
        report.error(where, "description must not contain XML/HTML tags")
    if len(frontmatter.get("compatibility", "")) > 500:
        report.error(where, "compatibility is longer than 500 chars")
    if not isinstance(metadata, dict):
        report.error(where, "metadata must be a map of string values")
        metadata = {}

    for key in frontmatter:
        if key not in SPEC_KEYS | CLAUDE_CODE_KEYS:
            report.warn(where, f"unknown frontmatter key '{key}'")

    # --- Repository conventions -------------------------------------------
    for key in REQUIRED_METADATA:
        if not metadata.get(key):
            report.error(where, f"metadata.{key} is required (see docs/AUTHORING.md)")
    version = metadata.get("version", "")
    if version and not SEMVER_PATTERN.match(version):
        report.error(where, f"metadata.version '{version}' is not semver (X.Y.Z)")
    if metadata.get("category") and metadata["category"] not in CATEGORIES:
        report.error(where, f"metadata.category must be one of {CATEGORIES}")
    if len(metadata.get("summary", "")) > 160:
        report.warn(where, "metadata.summary should fit in one line (<= 160 chars)")
    if not frontmatter.get("license"):
        report.warn(where, "no 'license' in frontmatter")

    line_count = len(skill["text"].splitlines())
    if line_count > MAX_SKILL_LINES:
        report.error(where, f"SKILL.md has {line_count} lines (max {MAX_SKILL_LINES}); move detail to references/")
    elif line_count > 350:
        report.warn(where, f"SKILL.md has {line_count} lines; consider moving detail to references/")

    for required in ("README.md", "CHANGELOG.md"):
        if not (path / required).exists():
            report.error(where, f"missing {required}")
    for document in ("SKILL.md", "README.md"):
        if (path / document).exists() and "TODO" in (path / document).read_text(encoding="utf-8"):
            report.error(where, f"{document} still has TODO markers")
    changelog = path / "CHANGELOG.md"
    if version and changelog.exists() and f"## [{version}]" not in changelog.read_text(encoding="utf-8"):
        report.error(where, f"CHANGELOG.md has no '## [{version}]' entry")

    # Links from SKILL.md and from every markdown file one level down.
    check_links(report, f"{where}/SKILL.md", path, skill["body"])
    references = path / "references"
    if references.exists():
        for doc in sorted(references.glob("*.md")):
            check_links(report, f"{where}/references/{doc.name}", references, doc.read_text(encoding="utf-8"))
            nested = re.findall(r"\]\((?:\./)?references/", doc.read_text(encoding="utf-8"))
            if nested:
                report.warn(where, f"references/{doc.name} links deeper into references/ — keep one level")

    # Files that installers drop or mangle: the skills CLI skips `metadata.json`,
    # `__pycache__/` and `__pypackages__/`; packaging tools often drop dotfiles.
    for file in path.rglob("*"):
        relative = file.relative_to(path).as_posix()
        parts = file.relative_to(path).parts
        if any(part in ("__pycache__", "__pypackages__") for part in parts):
            report.error(where, f"remove generated file {relative}")
            continue
        if file.name == "metadata.json":
            report.error(where, f"'{relative}' — installers skip files named metadata.json")
        if any(part.startswith(".") for part in parts):
            report.error(where, f"dotfile '{relative}' — store it without the dot and restore it in a script")


def check_catalog(report):
    try:
        marketplace, readme = build_catalog()
    except (ValueError, FrontmatterError, KeyError) as error:
        report.error("catalog", str(error))
        return
    if marketplace != load_marketplace():
        report.error(".claude-plugin/marketplace.json", "out of date — run `python scripts/sync_catalog.py`")
    if readme != README.read_text(encoding="utf-8"):
        report.error("README.md", "skills catalog out of date — run `python scripts/sync_catalog.py`")
    owner = marketplace.get("owner", {}).get("name", "")
    if not owner:
        report.error(".claude-plugin/marketplace.json", "owner.name is required")


def main(argv):
    report = Report()
    selected = set(argv)
    paths = [path for path in skill_dirs() if not selected or path.name in selected]
    if not paths:
        report.error("skills", f"no skills found in {SKILLS_DIR}")
    for path in paths:
        check_skill(report, path)
    if not selected:
        check_catalog(report)

    for line in report.warnings + report.errors:
        print(line)
    status = "FAILED" if report.errors else "OK"
    print(f"\n{status}: {len(paths)} skill(s), {len(report.errors)} error(s), {len(report.warnings)} warning(s).")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

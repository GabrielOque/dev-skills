"""
Shared helpers for the repository scripts (standard library only).

The frontmatter of each `skills/<name>/SKILL.md` is the single source of
truth for a skill's identity: `sync_catalog.py` derives the marketplace and
the README catalog from it, and `validate_skills.py` enforces the rules.

Supported frontmatter subset (keep SKILL.md files inside it):

    key: value                 plain or quoted scalar
    key: >-                    folded block (also >, |, |-), indented lines below
    key:                       a map of scalars, indented "  subkey: value" lines
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
TEMPLATE_DIR = ROOT / "template"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"

CATALOG_START = "<!-- skills-catalog:start -->"
CATALOG_END = "<!-- skills-catalog:end -->"

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
CATEGORIES = ("development", "productivity", "documentation", "data", "operations", "design")


class FrontmatterError(ValueError):
    pass


def _scalar(raw):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def parse_frontmatter(text):
    """Return (frontmatter dict, body str). Raises FrontmatterError."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("SKILL.md must start with '---' frontmatter")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration as error:
        raise FrontmatterError("frontmatter is not closed with '---'") from error

    data, index, block = {}, 0, lines[1:end]
    while index < len(block):
        line = block[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line.startswith((" ", "\t")):
            raise FrontmatterError(f"unexpected indentation: {line!r}")
        if ":" not in line:
            raise FrontmatterError(f"expected 'key: value': {line!r}")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        index += 1

        if value in (">", ">-", "|", "|-"):
            chunk = []
            while index < len(block) and (block[index].startswith((" ", "\t")) or not block[index].strip()):
                chunk.append(block[index].strip())
                index += 1
            if value.startswith(">"):
                data[key] = " ".join(part for part in chunk if part)
            else:
                data[key] = "\n".join(chunk).strip("\n")
        elif value == "":
            mapping = {}
            while index < len(block) and block[index].startswith((" ", "\t")):
                sub = block[index].strip()
                index += 1
                if not sub or sub.startswith("#"):
                    continue
                if ":" not in sub:
                    raise FrontmatterError(f"expected 'subkey: value' under {key}: {sub!r}")
                sub_key, sub_value = sub.split(":", 1)
                mapping[sub_key.strip()] = _scalar(sub_value)
            data[key] = mapping
        else:
            data[key] = _scalar(value)

    body = "\n".join(lines[end + 1 :])
    return data, body


def skill_dirs():
    if not SKILLS_DIR.exists():
        return []
    return sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())


def load_skill(path):
    """Frontmatter + body of one skill directory."""
    skill_md = path / "SKILL.md"
    data, body = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    return {"dir": path, "frontmatter": data, "body": body, "text": skill_md.read_text(encoding="utf-8")}


def load_marketplace():
    return json.loads(MARKETPLACE.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def tags_of(metadata):
    return [tag.strip() for tag in metadata.get("tags", "").split(",") if tag.strip()]


def plugin_entry(skill):
    """The marketplace entry derived from a skill's frontmatter."""
    frontmatter = skill["frontmatter"]
    metadata = frontmatter.get("metadata", {})
    name = frontmatter["name"]
    entry = {
        "name": name,
        "source": "./",
        "strict": False,
        "description": metadata.get("summary", ""),
        "version": metadata.get("version", ""),
        "category": metadata.get("category", ""),
        "tags": tags_of(metadata),
        "skills": [f"./skills/{name}"],
    }
    if frontmatter.get("license"):
        entry["license"] = frontmatter["license"]
    return entry


def catalog_table(skills):
    rows = [
        "| Skill | Versión | Categoría | Qué hace |",
        "| --- | --- | --- | --- |",
    ]
    for skill in skills:
        frontmatter = skill["frontmatter"]
        metadata = frontmatter.get("metadata", {})
        name = frontmatter["name"]
        rows.append(
            f"| [`{name}`](skills/{name}/) | {metadata.get('version', '')} | "
            f"{metadata.get('category', '')} | {metadata.get('summary', '')} |"
        )
    return "\n".join(rows)


def replace_catalog(readme_text, table):
    pattern = re.compile(re.escape(CATALOG_START) + r".*?" + re.escape(CATALOG_END), re.S)
    if not pattern.search(readme_text):
        raise ValueError(f"README.md has no {CATALOG_START} … {CATALOG_END} block")
    return pattern.sub(lambda _: f"{CATALOG_START}\n{table}\n{CATALOG_END}", readme_text)

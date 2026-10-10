#!/usr/bin/env python3
"""
Copy the PDN templates into a project directory.

    # Backend: creates the whole repository in an empty (or new) directory
    python scaffold.py backend  --target ../acme-back  --project-name "Acme Platform"

    # Frontend: overlays the structure on a fresh `create-next-app` project
    python scaffold.py frontend --target ../acme-front --project-name "Acme Platform"

Options:
    --time-zone   IANA time zone for the backend default   (default: UTC)
    --html-lang   <html lang> of the frontend and emails  (default: es)
    --force       write into a non-empty backend target / overwrite files

What it does besides copying:
- replaces {{PROJECT_NAME}}, {{PROJECT_SLUG}}, {{PROJECT_DB}}, {{TIME_ZONE}},
  {{HTML_LANG}} and {{PYTHON_VERSION}} in every text file;
- restores dotfiles stored without the dot (`gitignore`, `env.example`,
  `python-version`, `github/`) — installers and package managers drop dotfiles;
- frontend only: merges the path aliases of `tsconfig.paths.json` into the
  project's `tsconfig.json`, un-ignores `.env.example` and removes the
  create-next-app demo files that the structure replaces.

Standard library only. Prints the files it wrote.
"""

import argparse
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = {
    "backend": SKILL_DIR / "assets" / "backend",
    "frontend": SKILL_DIR / "assets" / "frontend",
}
DOTFILE_NAMES = {
    "gitignore": ".gitignore",
    "env.example": ".env.example",
    "python-version": ".python-version",
    "github": ".github",
}
SKIP_NAMES = {"__pycache__", ".DS_Store", "Thumbs.db"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".woff", ".woff2"}
TSCONFIG_PATHS = "tsconfig.paths.json"
CREATE_NEXT_APP_DEMO_FILES = (
    "app/page.module.css",
    "public/file.svg",
    "public/globe.svg",
    "public/next.svg",
    "public/vercel.svg",
    "public/window.svg",
)


def slugify(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "project"


def build_context(args):
    slug = slugify(args.project_name)
    return {
        "{{PROJECT_NAME}}": args.project_name.strip(),
        "{{PROJECT_SLUG}}": slug,
        "{{PROJECT_DB}}": slug.replace("-", "_"),
        "{{TIME_ZONE}}": args.time_zone,
        "{{HTML_LANG}}": args.html_lang,
        "{{PYTHON_VERSION}}": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


def destination_for(relative):
    return Path(*[DOTFILE_NAMES.get(part, part) for part in relative.parts])


def iter_template_files(root):
    for path in sorted(root.rglob("*")):
        if path.is_file() and not any(part in SKIP_NAMES for part in path.relative_to(root).parts):
            yield path


def render(source, target, context):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() in BINARY_SUFFIXES:
        shutil.copyfile(source, target)
        return
    text = source.read_text(encoding="utf-8")
    for token, value in context.items():
        text = text.replace(token, value)
    target.write_text(text, encoding="utf-8", newline="\n")


def copy_tree(template_root, target_root, context, skip=()):
    written = []
    for source in iter_template_files(template_root):
        relative = source.relative_to(template_root)
        if relative.as_posix() in skip:
            continue
        target = target_root / destination_for(relative)
        render(source, target, context)
        written.append(target.relative_to(target_root).as_posix())
    return written


def scaffold_backend(args, context):
    target = Path(args.target).resolve()
    if target.exists() and any(target.iterdir()) and not args.force:
        sys.exit(f"error: {target} is not empty (use --force to write into it anyway)")
    target.mkdir(parents=True, exist_ok=True)
    return copy_tree(TEMPLATES["backend"], target, context)


def merge_tsconfig_paths(target):
    template = json.loads((TEMPLATES["frontend"] / TSCONFIG_PATHS).read_text(encoding="utf-8"))
    tsconfig_path = target / "tsconfig.json"
    try:
        tsconfig = json.loads(tsconfig_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return (
            "WARNING: could not parse tsconfig.json — merge compilerOptions.paths from "
            f"{TEMPLATES['frontend'] / TSCONFIG_PATHS} by hand."
        )
    options = tsconfig.setdefault("compilerOptions", {})
    options["paths"] = {**options.get("paths", {}), **template["compilerOptions"]["paths"]}
    tsconfig_path.write_text(json.dumps(tsconfig, indent=2) + "\n", encoding="utf-8", newline="\n")
    return "tsconfig.json: path aliases merged"


def ensure_env_example_tracked(target):
    gitignore = target / ".gitignore"
    lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    if "!.env.example" in lines:
        return None
    lines += ["", "# The documented environment template is committed.", "!.env.example"]
    gitignore.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return ".gitignore: !.env.example added"


def scaffold_frontend(args, context):
    target = Path(args.target).resolve()
    package_json = target / "package.json"
    try:
        package = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        sys.exit(f"error: {package_json} not found — run create-next-app first (see SKILL.md, phase 3)")
    if "next" not in {**package.get("dependencies", {}), **package.get("devDependencies", {})}:
        sys.exit(f"error: {target} is not a Next.js project")

    written = copy_tree(TEMPLATES["frontend"], target, context, skip={TSCONFIG_PATHS})
    notes = [merge_tsconfig_paths(target), ensure_env_example_tracked(target)]
    for demo in CREATE_NEXT_APP_DEMO_FILES:
        path = target / demo
        if path.exists():
            path.unlink()
            notes.append(f"removed create-next-app demo file {demo}")
    return written, [note for note in notes if note]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=sorted(TEMPLATES))
    parser.add_argument("--target", required=True, help="project directory")
    parser.add_argument("--project-name", required=True, help='human name, e.g. "Acme Platform"')
    parser.add_argument("--time-zone", default="UTC", help="IANA time zone, e.g. America/Bogota")
    parser.add_argument("--html-lang", default="es", help="UI language for <html lang> and emails")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    context = build_context(args)
    if args.kind == "backend":
        written, notes = scaffold_backend(args, context), []
    else:
        written, notes = scaffold_frontend(args, context)

    print(f"{args.kind}: {len(written)} files written to {Path(args.target).resolve()}")
    for path in written:
        print(f"  {path}")
    for note in notes:
        print(note)
    return 0


if __name__ == "__main__":
    sys.exit(main())

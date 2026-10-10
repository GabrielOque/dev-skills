#!/usr/bin/env python3
"""
Pin every line of a requirements.txt to the version installed in a virtualenv.

    python pin_requirements.py <backend-dir> [--python <path-to-venv-python>]

Reads `<backend-dir>/requirements.txt`, asks the virtualenv's pip what is
installed (`pip freeze`), and rewrites each requirement as `name[extras]==X.Y.Z`.
Comments, blank lines and already-pinned lines are kept as they are. The
default interpreter is `<backend-dir>/.venv` (Scripts/python.exe on Windows,
bin/python elsewhere).

Standard library only.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

REQUIREMENT = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?P<extras>\[[^\]]+\])?\s*$")


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def default_python(backend):
    for candidate in (backend / ".venv" / "Scripts" / "python.exe", backend / ".venv" / "bin" / "python"):
        if candidate.exists():
            return candidate
    sys.exit("error: no .venv found; pass --python <interpreter>")


def installed_versions(python):
    output = subprocess.run(
        [str(python), "-m", "pip", "freeze", "--disable-pip-version-check"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    versions = {}
    for line in output.splitlines():
        if "==" in line:
            name, version = line.split("==", 1)
            versions[canonical(name)] = version.strip()
    return versions


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("backend", type=Path)
    parser.add_argument("--python", type=Path)
    args = parser.parse_args()

    requirements = args.backend / "requirements.txt"
    versions = installed_versions(args.python or default_python(args.backend))

    pinned, missing, lines = [], [], []
    for line in requirements.read_text(encoding="utf-8").splitlines():
        match = REQUIREMENT.match(line.strip())
        if not match:
            lines.append(line)
            continue
        name, extras = match.group("name"), match.group("extras") or ""
        version = versions.get(canonical(name))
        if version is None:
            missing.append(name)
            lines.append(line)
            continue
        lines.append(f"{name}{extras}=={version}")
        pinned.append(f"{name}=={version}")

    requirements.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Pinned {len(pinned)}: " + ", ".join(pinned))
    if missing:
        print("Not installed (left unpinned): " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

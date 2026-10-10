"""
Fast checks of the initial-setup-pdn-stack templates and scripts (no network,
no database). The full integration — install, migrate, test, build — runs in
.github/workflows/initial-setup-pdn-stack.yml.
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skills" / "initial-setup-pdn-stack"
SCAFFOLD = SKILL / "scripts" / "scaffold.py"
PERMISSION_ROWS = SKILL / "scripts" / "permission_rows.py"
LEFTOVER_PLACEHOLDER = re.compile(r"\{\{[A-Z][A-Z_]+\}\}")


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")


def text_files(root):
    for path in Path(root).rglob("*"):
        if path.is_file() and path.suffix not in {".png", ".ico"}:
            yield path


class BackendScaffoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.target = Path(cls.tmp.name) / "acme-back"
        cls.result = run(
            SCAFFOLD, "backend", "--target", cls.target, "--project-name", "Acme Plátform", "--time-zone", "America/Bogota"
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_scaffold_succeeds(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)

    def test_dotfiles_are_restored(self):
        for name in (".gitignore", ".env.example", ".python-version", ".github/workflows/ci.yml"):
            self.assertTrue((self.target / name).exists(), name)
        for name in ("gitignore", "env.example", "python-version", "github"):
            self.assertFalse((self.target / name).exists(), name)

    def test_no_placeholder_is_left(self):
        for path in text_files(self.target):
            leftover = LEFTOVER_PLACEHOLDER.findall(path.read_text(encoding="utf-8"))
            self.assertEqual(leftover, [], f"{path.relative_to(self.target)}: {leftover}")

    def test_placeholders_are_filled(self):
        env_example = (self.target / ".env.example").read_text(encoding="utf-8")
        self.assertIn("PROJECT_NAME=Acme Plátform", env_example)
        self.assertIn("DB_NAME=acme_platform", env_example)
        self.assertIn("TIME_ZONE=America/Bogota", env_example)

    def test_every_python_file_compiles(self):
        # In memory: py_compile would drop __pycache__ into the generated tree.
        for path in self.target.rglob("*.py"):
            compile(path.read_text(encoding="utf-8"), str(path), "exec")

    def test_every_package_has_an_init(self):
        for directory in ("config", "common", "common/decorators", "accounts", "users/models", "users/views"):
            self.assertTrue((self.target / directory / "__init__.py").exists(), directory)

    def test_refuses_a_non_empty_target(self):
        result = run(SCAFFOLD, "backend", "--target", self.target, "--project-name", "Again")
        self.assertNotEqual(result.returncode, 0)


class FrontendScaffoldTests(unittest.TestCase):
    def make_next_project(self, root):
        project = Path(root) / "acme-front"
        (project / "app").mkdir(parents=True)
        (project / "public").mkdir()
        (project / "package.json").write_text(json.dumps({"dependencies": {"next": "16.0.0"}}), encoding="utf-8")
        (project / "tsconfig.json").write_text(
            json.dumps({"compilerOptions": {"strict": True, "paths": {"@/*": ["./*"]}}}), encoding="utf-8"
        )
        (project / ".gitignore").write_text(".env*\n", encoding="utf-8")
        (project / "app" / "page.module.css").write_text("", encoding="utf-8")
        (project / "public" / "next.svg").write_text("", encoding="utf-8")
        return project

    def test_overlay_on_a_next_project(self):
        with tempfile.TemporaryDirectory() as root:
            project = self.make_next_project(root)
            result = run(SCAFFOLD, "frontend", "--target", project, "--project-name", "Acme", "--html-lang", "es")
            self.assertEqual(result.returncode, 0, result.stderr)

            for name in ("proxy.ts", "actions/api-client.ts", "redux/store.ts", "libs/routes.ts", ".env.example"):
                self.assertTrue((project / name).exists(), name)
            self.assertFalse((project / "tsconfig.paths.json").exists())
            self.assertFalse((project / "app" / "page.module.css").exists())
            self.assertFalse((project / "public" / "next.svg").exists())

            paths = json.loads((project / "tsconfig.json").read_text(encoding="utf-8"))["compilerOptions"]["paths"]
            for alias in ("@/a", "@/c/*", "@/h", "@/l/*", "@/pc/*", "@/r/*", "@/t"):
                self.assertIn(alias, paths)
            self.assertIn("!.env.example", (project / ".gitignore").read_text(encoding="utf-8"))
            self.assertIn('lang="es"', (project / "app" / "layout.tsx").read_text(encoding="utf-8"))

            for path in text_files(project):
                self.assertEqual(LEFTOVER_PLACEHOLDER.findall(path.read_text(encoding="utf-8")), [], path)

    def test_refuses_a_directory_without_next(self):
        with tempfile.TemporaryDirectory() as root:
            result = run(SCAFFOLD, "frontend", "--target", root, "--project-name", "Acme")
            self.assertNotEqual(result.returncode, 0)


class PermissionCatalogueTests(unittest.TestCase):
    FIXTURE = SKILL / "assets" / "backend" / "users" / "fixtures" / "permissions_catalog.json"

    def test_base_fixture_is_valid(self):
        result = run(PERMISSION_ROWS, "--check", self.FIXTURE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rows_have_deterministic_pks(self):
        first = run(PERMISSION_ROWS, "projects.tasks.view=Ver tareas")
        second = run(PERMISSION_ROWS, "projects.tasks.view=Ver tareas")
        self.assertEqual(json.loads(first.stdout)[0]["pk"], json.loads(second.stdout)[0]["pk"])

    def test_invalid_codename_is_rejected(self):
        self.assertNotEqual(run(PERMISSION_ROWS, "Bad Codename=x").returncode, 0)


if __name__ == "__main__":
    unittest.main()

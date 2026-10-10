"""Tests for the repository tools in scripts/ (standard library only)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import skills_lib  # noqa: E402
import validate_skills  # noqa: E402


class FrontmatterParserTests(unittest.TestCase):
    def test_scalars_folded_blocks_and_metadata_map(self):
        text = (
            "---\n"
            "name: demo-skill\n"
            "description: >-\n"
            "  First line\n"
            "  second line.\n"
            'license: "MIT"\n'
            "metadata:\n"
            '  version: "1.2.3"\n'
            "  summary: Una línea\n"
            "---\n"
            "# Body\n"
        )
        data, body = skills_lib.parse_frontmatter(text)
        self.assertEqual(data["name"], "demo-skill")
        self.assertEqual(data["description"], "First line second line.")
        self.assertEqual(data["license"], "MIT")
        self.assertEqual(data["metadata"], {"version": "1.2.3", "summary": "Una línea"})
        self.assertEqual(body.strip(), "# Body")

    def test_missing_frontmatter_is_an_error(self):
        with self.assertRaises(skills_lib.FrontmatterError):
            skills_lib.parse_frontmatter("# no frontmatter\n")


class ValidatorTests(unittest.TestCase):
    def make_skill(self, root, name, frontmatter_name=None, extra_files=()):
        path = Path(root) / name
        path.mkdir()
        (path / "SKILL.md").write_text(
            "---\n"
            f"name: {frontmatter_name or name}\n"
            "description: Does a thing. Use when the user asks for the thing.\n"
            "license: MIT\n"
            "metadata:\n"
            '  version: "1.0.0"\n'
            '  summary: "Hace una cosa."\n'
            '  category: "development"\n'
            "---\n# Skill\n",
            encoding="utf-8",
        )
        (path / "README.md").write_text("# readme\n", encoding="utf-8")
        (path / "CHANGELOG.md").write_text("## [1.0.0] - 2026-01-01\n", encoding="utf-8")
        for relative in extra_files:
            target = path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x", encoding="utf-8")
        return path

    def check(self, path):
        report = validate_skills.Report()
        validate_skills.check_skill(report, path)
        return report

    def test_a_correct_skill_passes(self):
        with tempfile.TemporaryDirectory() as root:
            report = self.check(self.make_skill(root, "good-skill"))
            self.assertEqual(report.errors, [])

    def test_name_must_match_directory(self):
        with tempfile.TemporaryDirectory() as root:
            report = self.check(self.make_skill(root, "dir-name", frontmatter_name="other-name"))
            self.assertTrue(any("must match the directory" in error for error in report.errors))

    def test_dotfiles_and_metadata_json_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.make_skill(root, "files-skill", extra_files=["assets/.env.example", "assets/metadata.json"])
            report = self.check(path)
            self.assertTrue(any("dotfile" in error for error in report.errors))
            self.assertTrue(any("metadata.json" in error for error in report.errors))

    def test_broken_link_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.make_skill(root, "links-skill")
            skill_md = path / "SKILL.md"
            skill_md.write_text(skill_md.read_text(encoding="utf-8") + "\nSee [x](references/missing.md).\n")
            report = self.check(path)
            self.assertTrue(any("broken link" in error for error in report.errors))


class RepositoryStateTests(unittest.TestCase):
    """The committed repository must always validate and be in sync."""

    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
        )

    def test_repository_validates(self):
        result = self.run_script("scripts/validate_skills.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_catalog_is_in_sync(self):
        result = self.run_script("scripts/sync_catalog.py", "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

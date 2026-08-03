from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from audit_public_tree import _content_violations, audit_public_tree


class PublicTreeAuditTests(unittest.TestCase):
    def test_public_audit_narrowly_allows_dev_requirements_at_root(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "requirements-dev.txt").write_text(
                "Pillow>=12.2,<13\n", encoding="utf-8"
            )
            (root / "requirements.txt").write_text("unreviewed\n", encoding="utf-8")

            errors = audit_public_tree(root)

        self.assertFalse(any("requirements-dev.txt" in error for error in errors))
        self.assertTrue(any("requirements.txt" in error for error in errors))

    def test_public_audit_rejects_raw_and_secret_files(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "exam.pdf").write_bytes(b"raw")
            (root / ".env").write_text(
                "GITHUB_" + "TOKEN" + "=" + "secret" + "\n",
                encoding="utf-8",
            )

            errors = audit_public_tree(root)

        self.assertTrue(any("exam.pdf" in error for error in errors))
        self.assertTrue(any(".env" in error for error in errors))

    def test_public_audit_allows_only_named_release_archives(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dist = root / "dist"
            dist.mkdir()
            (dist / "ctis.skill").write_bytes(b"skill")
            (dist / "ctis-codex-plugin.zip").write_bytes(b"codex")
            (dist / "ctis-claude-plugin.zip").write_bytes(b"claude")

            errors = audit_public_tree(root)

        self.assertEqual([], errors)

    def test_public_audit_rejects_release_archive_near_misses_and_other_roots(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dist = root / "dist"
            dist.mkdir()
            (dist / "ctis-codex-plugin-copy.zip").write_bytes(b"near miss")
            (dist / "ctis-copy.skill").write_bytes(b"near miss")
            examples = root / "examples"
            examples.mkdir()
            (examples / "ctis-codex-plugin.zip").write_bytes(b"wrong root")
            (examples / "ctis.skill").write_bytes(b"wrong root")

            errors = audit_public_tree(root)

        self.assertEqual(2, sum("forbidden file extension .zip" in error for error in errors))
        self.assertEqual(2, sum("forbidden file extension .skill" in error for error in errors))

    def test_public_audit_rejects_home_paths_and_student_ids(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "README.md").write_text(
                "C:" + "\\" + "Users" + "\\" + "learner" + "\\" + "private\n"
                + "Student " + "ID" + ": 12345678\n",
                encoding="utf-8",
            )

            errors = audit_public_tree(root)

        self.assertTrue(any("home path" in error for error in errors))
        self.assertTrue(any("student identifier" in error for error in errors))

    def test_documentation_images_require_source_declaration(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            assets = root / "docs" / "assets"
            assets.mkdir(parents=True)
            (assets / "person.jpg").write_bytes(b"image")
            (assets / "sources.json").write_text(
                json.dumps({"assets": []}), encoding="utf-8"
            )

            errors = audit_public_tree(root)

        self.assertTrue(any("docs/assets/person.jpg" in error for error in errors))
        self.assertTrue(any("source declaration" in error for error in errors))

    def test_public_audit_rejects_namespaced_credential_assignments(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "README.md").write_text(
                "OPENAI_" + "API_" + "KEY=secret\n"
                + "AWS_" + "SECRET_" + "ACCESS_" + "KEY=secret\n",
                encoding="utf-8",
            )

            errors = audit_public_tree(root)

        self.assertEqual(2, sum("credential assignment" in error for error in errors))

    def test_public_audit_rejects_semantic_raw_material_paths(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            materials = root / "docs" / ("exam" + "-notes")
            materials.mkdir(parents=True)
            (materials / "outline.md").write_text("outline", encoding="utf-8")
            submissions = root / "tests" / ("student" + "-submissions")
            submissions.mkdir(parents=True)
            (submissions / "answer.txt").write_text("answer", encoding="utf-8")
            extracted = root / "docs" / ("extracted" + "-text.md")
            extracted.write_text("text", encoding="utf-8")

            errors = audit_public_tree(root)

        self.assertEqual(3, sum("raw course material marker" in error for error in errors))

    def test_public_audit_rejects_generic_absolute_local_paths(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "README.md").write_text(
                "D:" + "\\" + "workspace" + "\\" + "private\n"
                + "/" + "developer/private\n"
                + "https://bilkent.edu.tr/ctis\n",
                encoding="utf-8",
            )

            errors = audit_public_tree(root)

        self.assertEqual(2, sum("absolute local path" in error for error in errors))

    def test_documentation_asset_sources_require_official_structured_metadata(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            assets = root / "docs" / "assets"
            assets.mkdir(parents=True)
            (assets / "person.jpg").write_bytes(b"image")
            (assets / "sources.json").write_text(
                json.dumps(
                    {
                        "assets": [
                            {
                                "path": "person.jpg",
                                "source_page": "https://bilkent.edu.tr/ctis",
                                "source_url": "https://example.test/person.jpg",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            errors = audit_public_tree(root)

        self.assertTrue(any("rights_note" in error for error in errors))
        self.assertTrue(any("source_url" in error for error in errors))

    def test_safe_public_fixture_passes(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "README.md").write_text("# CTIS Skills\n", encoding="utf-8")
            skill = root / "skills" / "ctis"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# CTIS\n", encoding="utf-8")
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_public_tree.py").write_text("# test fixture\n", encoding="utf-8")

            errors = audit_public_tree(root)

        self.assertEqual([], errors)

    def test_audit_rejects_paths_outside_public_roots(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            private = root / "private"
            private.mkdir()
            (private / "notes.md").write_text("private", encoding="utf-8")

            errors = audit_public_tree(root)

        self.assertTrue(any("private/notes.md" in error for error in errors))
        self.assertTrue(any("approved public roots" in error for error in errors))

    def test_gitignore_uses_a_release_allowlist(self) -> None:
        lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        rules = {line.strip() for line in lines if line.strip() and not line.startswith("#")}

        self.assertEqual("*", next(line for line in lines if line.strip()))
        for root in (
            ".claude-plugin",
            ".codex-plugin",
            "skills",
            "tools",
            "tests",
            "docs",
            "examples",
            "dist",
        ):
            self.assertIn(f"!/{root}/", rules)
            self.assertIn(f"!/{root}/**", rules)
        self.assertIn("/.worktrees/", rules)
        self.assertIn("/.superpowers/sdd/", rules)
        self.assertIn("/" + "docs/superpowers/", rules)

    def test_gitattributes_pins_lf_so_clones_rebuild_identical_packages(self) -> None:
        rules = {
            line.strip()
            for line in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }

        self.assertIn("* text=auto eol=lf", rules)
        for pattern in ("*.png binary", "*.zip binary", "*.skill binary"):
            self.assertIn(pattern, rules)

        source_files = [
            path for path in (ROOT / "skills" / "ctis").rglob("*") if path.is_file()
        ]
        self.assertTrue(source_files)
        self.assertEqual(
            [], [path.name for path in source_files if b"\r\n" in path.read_bytes()]
        )

    def test_direct_gitignore_content_scan_returns_no_violations(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            candidate = Path(temporary_directory) / ".gitignore"
            candidate.write_text("*\n", encoding="utf-8")

            errors = _content_violations(".gitignore", candidate)

        self.assertEqual([], errors)

    def test_internal_development_records_are_rejected_when_audited(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            planning = root / "docs" / "superpowers" / "plans"
            planning.mkdir(parents=True)
            (planning / "internal.md").write_text(
                "D:" + "\\" + "workspace" + "\\" + "private\n"
                + "OPENAI_" + "API_" + "KEY=secret\n",
                encoding="utf-8",
            )

            errors = audit_public_tree(root, ["docs/superpowers/plans/internal.md"])

        self.assertTrue(any("credential assignment" in error for error in errors))
        self.assertTrue(any("absolute local path" in error for error in errors))

    def test_internal_planning_docs_are_not_tracked(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()

        self.assertFalse(any(path.startswith("docs/superpowers/") for path in tracked))


if __name__ == "__main__":
    unittest.main()

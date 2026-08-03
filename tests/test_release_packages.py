from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "ctis"
COURSES = (
    "ctis151", "ctis163", "ctis164", "ctis166", "ctis255", "ctis256",
    "ctis259", "ctis262", "ctis264", "ctis359", "ctis411", "ctis465", "ctis474",
)
SEMANTIC_FILES = {
    "SKILL.md",
    "references/capability-primitives.md",
    "references/evidence-policy.md",
    "scripts/validate_ctis_skill.py",
    *(f"references/courses/{course}.md" for course in COURSES),
}
CANONICAL_FILES = SEMANTIC_FILES | {"agents/openai.yaml"}
ARTIFACT_NAMES = (
    "ctis.skill",
    "ctis-codex-plugin.zip",
    "ctis-claude-plugin.zip",
)
COMMAND_FILES = {f"{course[4:]}.md" for course in COURSES}


def _load_packages_module():
    path = ROOT / "tools" / "build_ctis_packages.py"
    spec = importlib.util.spec_from_file_location("build_ctis_packages", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if archive.testzip() is not None:
            raise AssertionError(f"corrupt test artifact: {path}")
        return {name: archive.read(name) for name in names}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReleasePackageTests(unittest.TestCase):
    def test_release_set_has_exact_members_and_byte_parity(self) -> None:
        packages = _load_packages_module()
        with TemporaryDirectory() as temporary_directory:
            outputs = packages.build_release_set(SOURCE, Path(temporary_directory))

            self.assertEqual(set(ARTIFACT_NAMES), set(outputs))
            skill = _members(outputs["ctis.skill"])
            codex = _members(outputs["ctis-codex-plugin.zip"])
            claude = _members(outputs["ctis-claude-plugin.zip"])

        expected_skill = {f"ctis/{name}" for name in CANONICAL_FILES}
        expected_codex = {
            "ctis/.codex-plugin/plugin.json",
            *(f"ctis/skills/ctis/{name}" for name in CANONICAL_FILES),
            *(f"ctis/commands/{name}" for name in COMMAND_FILES),
        }
        expected_claude = {
            "ctis/.claude-plugin/plugin.json",
            "ctis/.claude-plugin/marketplace.json",
            "ctis/plugin.json",
            *(f"ctis/skills/ctis/{name}" for name in SEMANTIC_FILES),
            *(f"ctis/commands/{name}" for name in COMMAND_FILES),
        }
        self.assertEqual(expected_skill, set(skill))
        self.assertEqual(expected_codex, set(codex))
        self.assertEqual(expected_claude, set(claude))
        for relative in sorted(CANONICAL_FILES):
            expected = (SOURCE / relative).read_bytes()
            with self.subTest(platform="skill", relative=relative):
                self.assertEqual(expected, skill[f"ctis/{relative}"])
            with self.subTest(platform="codex", relative=relative):
                self.assertEqual(expected, codex[f"ctis/skills/ctis/{relative}"])
        for relative in sorted(SEMANTIC_FILES):
            with self.subTest(platform="claude", relative=relative):
                self.assertEqual(
                    (SOURCE / relative).read_bytes(),
                    claude[f"ctis/skills/ctis/{relative}"],
                )
        for name in sorted(COMMAND_FILES):
            expected = (ROOT / "commands" / name).read_bytes()
            with self.subTest(platform="codex-command", command=name):
                self.assertEqual(expected, codex[f"ctis/commands/{name}"])
            with self.subTest(platform="claude-command", command=name):
                self.assertEqual(expected, claude[f"ctis/commands/{name}"])
        self.assertEqual(
            (ROOT / ".codex-plugin" / "plugin.json").read_bytes(),
            codex["ctis/.codex-plugin/plugin.json"],
        )
        self.assertEqual(
            (ROOT / ".claude-plugin" / "plugin.json").read_bytes(),
            claude["ctis/.claude-plugin/plugin.json"],
        )
        self.assertEqual(
            (ROOT / ".claude-plugin" / "marketplace.json").read_bytes(),
            claude["ctis/.claude-plugin/marketplace.json"],
        )
        self.assertEqual(
            (ROOT / "plugin.json").read_bytes(),
            claude["ctis/plugin.json"],
        )

    def test_release_archives_have_stable_safe_zip_metadata(self) -> None:
        packages = _load_packages_module()
        with TemporaryDirectory() as temporary_directory:
            outputs = packages.build_release_set(SOURCE, Path(temporary_directory))

            for artifact_name in ARTIFACT_NAMES:
                with self.subTest(artifact=artifact_name), zipfile.ZipFile(outputs[artifact_name]) as archive:
                    infos = archive.infolist()
                    names = [info.filename for info in infos]
                    self.assertEqual(sorted(names), names)
                    self.assertEqual(len(names), len(set(names)))
                    self.assertFalse(any(name.endswith("/") for name in names))
                    for info in infos:
                        self.assertEqual((2026, 8, 2, 0, 0, 0), info.date_time)
                        self.assertEqual(3, info.create_system)
                        self.assertEqual(0o100644, info.external_attr >> 16)
                        self.assertFalse(info.external_attr >> 16 & 0o120000 == 0o120000)

    def test_two_output_directories_receive_byte_identical_archives(self) -> None:
        packages = _load_packages_module()
        with TemporaryDirectory() as first_directory, TemporaryDirectory() as second_directory:
            first = packages.build_release_set(SOURCE, Path(first_directory))
            second = packages.build_release_set(SOURCE, Path(second_directory))

            for artifact_name in ARTIFACT_NAMES:
                with self.subTest(artifact=artifact_name):
                    self.assertEqual(_sha256(first[artifact_name]), _sha256(second[artifact_name]))
                    self.assertEqual(first[artifact_name].read_bytes(), second[artifact_name].read_bytes())

    def test_replace_failure_restores_every_preexisting_artifact(self) -> None:
        packages = _load_packages_module()
        old_bytes = {
            "ctis.skill": b"old skill archive",
            "ctis-codex-plugin.zip": b"old codex archive",
            "ctis-claude-plugin.zip": b"old claude archive",
        }
        with TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            for name, data in old_bytes.items():
                (output_dir / name).write_bytes(data)

            real_replace = os.replace
            failed = False

            def fail_second_artifact_once(source, target):
                nonlocal failed
                if Path(target).name == "ctis-codex-plugin.zip" and not failed:
                    failed = True
                    raise OSError("injected second-artifact replace failure")
                return real_replace(source, target)

            with mock.patch.object(packages.os, "replace", new=fail_second_artifact_once):
                with self.assertRaisesRegex(OSError, "injected second-artifact"):
                    packages.build_release_set(SOURCE, output_dir)

            self.assertTrue(failed)
            self.assertEqual(old_bytes, {name: (output_dir / name).read_bytes() for name in ARTIFACT_NAMES})
            self.assertEqual(set(ARTIFACT_NAMES), {path.name for path in output_dir.iterdir()})

    def test_replace_failure_leaves_no_partial_new_artifacts(self) -> None:
        packages = _load_packages_module()
        with TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            real_replace = os.replace
            failed = False

            def fail_second_artifact_once(source, target):
                nonlocal failed
                if Path(target).name == "ctis-codex-plugin.zip" and not failed:
                    failed = True
                    raise OSError("injected second-artifact replace failure")
                return real_replace(source, target)

            with mock.patch.object(packages.os, "replace", new=fail_second_artifact_once):
                with self.assertRaisesRegex(OSError, "injected second-artifact"):
                    packages.build_release_set(SOURCE, output_dir)

            self.assertTrue(failed)
            self.assertEqual([], list(output_dir.iterdir()))


if __name__ == "__main__":
    unittest.main()

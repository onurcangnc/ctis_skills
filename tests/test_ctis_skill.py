from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "ctis"
COURSES = {
    "ctis151", "ctis163", "ctis164", "ctis166", "ctis255", "ctis256",
    "ctis259", "ctis262", "ctis264", "ctis359", "ctis411", "ctis417", "ctis465", "ctis474",
}
COMMAND_FILES = {f"{course[4:]}.md" for course in COURSES}
REQUIRED_SECTIONS = {
    "Teaching posture",
    "Scope",
    "Rules with rewrites",
    "Failure modes",
    "Verification",
    "Workflow",
}
FORBIDDEN_SUFFIXES = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg",
    ".heic", ".mp4", ".pkt", ".pka", ".db", ".sqlite", ".csproj",
}
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".py", ".txt"}
CANONICAL_FILES = {
    "SKILL.md",
    "agents/openai.yaml",
    "references/capability-primitives.md",
    "references/evidence-policy.md",
    *(f"references/courses/{course}.md" for course in COURSES),
    "scripts/validate_ctis_skill.py",
}


def _source_files() -> list[Path]:
    return sorted(path for path in SOURCE.rglob("*") if path.is_file()) if SOURCE.exists() else []


def _frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip('"\'')
    return result


def _archive_payload(path: Path, prefix: str) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        payload: dict[str, bytes] = {}
        for name in archive.namelist():
            if name.endswith("/") or not name.startswith(prefix):
                continue
            relative = name[len(prefix):]
            payload[relative] = archive.read(name)
        return payload


def _text_from_payload(payload: dict[str, bytes]) -> str:
    chunks: list[str] = []
    for name, data in payload.items():
        if PurePosixPath(name).suffix.lower() in TEXT_SUFFIXES:
            chunks.append(name)
            chunks.append(data.decode("utf-8", errors="replace"))
    return "\n".join(chunks).casefold()


class CTISSkillTests(unittest.TestCase):
    def _load_module(self, name: str, path: Path):
        self.assertTrue(path.is_file(), f"missing {path}")
        spec = importlib.util.spec_from_file_location(name, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        return module

    def _load_analyzer(self):
        return self._load_module("analyze_ctis_patterns", ROOT / "tools" / "analyze_ctis_patterns.py")

    def _load_builder(self):
        return self._load_module("build_ctis_packages", ROOT / "tools" / "build_ctis_packages.py")

    def _load_validator(self):
        return self._load_module(
            "validate_ctis_skill", SOURCE / "scripts" / "validate_ctis_skill.py"
        )

    def test_analyzer_matches_tokens_not_accidental_substrings(self) -> None:
        analyzer = self._load_analyzer()
        self.assertEqual("ctis465", analyzer.infer_course("CTIS 465/project/Program.cs"))
        self.assertEqual("ctis474", analyzer.infer_course("Audit-Study Case-1.docx"))
        self.assertIsNone(analyzer.infer_course("microserviceability-notes.txt"))
        self.assertIsNone(analyzer.infer_course("security-auditorium-layout.md"))
        self.assertEqual(
            "document",
            analyzer.classify_artifact("transportation/answerable-questions.pdf", ".pdf"),
        )
        self.assertEqual(
            "lab-guide-or-solution",
            analyzer.classify_artifact("CTIS262/LabGuide7_ANS.pdf", ".pdf"),
        )

    def test_analyzer_rejects_paths_outside_allowed_roots(self) -> None:
        analyzer = self._load_analyzer()
        with self.assertRaises(ValueError):
            analyzer.resolve_contained(ROOT, "../outside.txt", label="representative")
        with self.assertRaises(ValueError):
            analyzer.resolve_contained(
                ROOT / "analysis-root",
                ROOT / "tests" / "test_ctis_skill.py",
                label="extracted_text",
            )

    def test_source_has_exactly_one_skill(self) -> None:
        skill_files = [path for path in _source_files() if path.name == "SKILL.md"]
        self.assertEqual([SOURCE / "SKILL.md"], skill_files)

    def test_frontmatter_and_description_are_valid(self) -> None:
        path = SOURCE / "SKILL.md"
        self.assertTrue(path.is_file(), f"missing {path}")
        metadata = _frontmatter(path.read_text(encoding="utf-8"))
        self.assertEqual({"name", "description"}, set(metadata))
        self.assertEqual("ctis", metadata["name"])
        self.assertTrue(metadata["description"].startswith("Use when"))
        self.assertLessEqual(len(metadata["name"] + metadata["description"]), 1024)

    def test_all_course_modules_exist_and_are_routed(self) -> None:
        skill_path = SOURCE / "SKILL.md"
        self.assertTrue(skill_path.is_file(), f"missing {skill_path}")
        skill_text = skill_path.read_text(encoding="utf-8")
        for course in sorted(COURSES):
            path = SOURCE / "references" / "courses" / f"{course}.md"
            with self.subTest(course=course):
                self.assertTrue(path.is_file(), f"missing {path}")
                self.assertIn(f"references/courses/{course}.md", skill_text)
        actual_modules = {
            path.stem for path in (SOURCE / "references" / "courses").glob("*.md") if path.is_file()
        }
        self.assertEqual(COURSES, actual_modules)

    def test_every_course_module_has_required_sections(self) -> None:
        for course in sorted(COURSES):
            path = SOURCE / "references" / "courses" / f"{course}.md"
            self.assertTrue(path.is_file(), f"missing {path}")
            text = path.read_text(encoding="utf-8")
            headings = [
                match.group(1).strip()
                for match in re.finditer(r"(?m)^##\s+(.+?)\s*$", text)
            ]
            with self.subTest(course=course):
                self.assertTrue(
                    REQUIRED_SECTIONS.issubset(set(headings)),
                    REQUIRED_SECTIONS - set(headings),
                )
                self.assertGreaterEqual(
                    headings.index("Rules with rewrites") - headings.index("Scope"),
                    2,
                    "a shape section is required between Scope and Rules with rewrites",
                )
            for heading in REQUIRED_SECTIONS:
                body = re.search(
                    rf"(?ms)^## {re.escape(heading)}\s*\n(.+?)(?=^## |\Z)", text
                )
                with self.subTest(course=course, heading=heading):
                    self.assertIsNotNone(body)
                    self.assertTrue(body.group(1).strip())

    def test_scenario_capabilities_are_present(self) -> None:
        scenarios = json.loads((ROOT / "tests" / "scenario-contracts.json").read_text(encoding="utf-8"))
        self.assertEqual(COURSES, {scenario["course"] for scenario in scenarios})
        for scenario in scenarios:
            path = SOURCE / "references" / "courses" / f'{scenario["course"]}.md'
            self.assertTrue(path.is_file(), f"missing {path}")
            text = path.read_text(encoding="utf-8").casefold()
            for required in scenario["requires"]:
                with self.subTest(course=scenario["course"], required=required):
                    self.assertIn(required.casefold(), text)

    def test_every_course_has_a_command_contract(self) -> None:
        skill_text = (SOURCE / "SKILL.md").read_text(encoding="utf-8")
        commands_root = ROOT / "commands"
        for course in sorted(COURSES):
            command_path = commands_root / f"{course[4:]}.md"
            with self.subTest(course=course):
                self.assertTrue(command_path.is_file(), f"missing {command_path}")
                command_text = command_path.read_text(encoding="utf-8")
                self.assertTrue(command_text.startswith("---"), "missing frontmatter")
                self.assertRegex(command_text, r"(?m)^description:")
                self.assertIn("$ARGUMENTS", command_text)
                self.assertIn(
                    f"skills/ctis/references/courses/{course}.md", command_text
                )
                self.assertIn(f"/ctis:{course[4:]}", skill_text)
        actual_commands = {
            path.name for path in commands_root.glob("*.md") if path.is_file()
        }
        self.assertEqual({f"{course[4:]}.md" for course in COURSES}, actual_commands)

    def test_distributed_text_is_anonymous(self) -> None:
        blocked = [
            line.strip().casefold()
            for line in (ROOT / "tests" / "forbidden-identifiers.txt").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        source_text = "\n".join(
            [str(path.relative_to(SOURCE)) for path in _source_files()]
            + [path.read_text(encoding="utf-8", errors="replace") for path in _source_files() if path.suffix.lower() in TEXT_SUFFIXES]
        ).casefold()
        for identifier in blocked:
            with self.subTest(source_identifier=identifier):
                self.assertFalse(identifier in source_text, f"identity leak: {identifier}")

    def test_generic_privacy_patterns_cover_unknown_identifiers(self) -> None:
        validator = self._load_validator()
        fixtures = (
            ("notes.md", "Contact learner42@example.org"),
            ("notes.md", "C:" + "\\" + "Users" + "\\learner42\\private\\notes.txt"),
            ("notes.md", "/" + "home/learner42/private/notes.txt"),
            ("notes.md", "https://github.com/learner42/course-work"),
            ("notes.md", "Student " + "ID: 12345678"),
            ("notes.yaml", "instructor: Example Person"),
            ("profile.md", "# Instructor biography"),
            ("student-submission.md", "technical content"),
        )
        for relative, text in fixtures:
            with self.subTest(relative=relative, text=text):
                self.assertTrue(validator.privacy_errors(PurePosixPath(relative), text))
        generic_manifest = json.dumps({"author": {"name": "CTIS Capability Studio"}})
        self.assertEqual(
            [],
            validator.privacy_errors(PurePosixPath(".codex-plugin/plugin.json"), generic_manifest),
        )

    def test_validator_rejects_unexpected_hidden_and_empty_contract_files(self) -> None:
        validator = self._load_validator()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "ctis"
            shutil.copytree(SOURCE, root)
            (root / ".env").write_text("TOKEN" + "=value\n", encoding="utf-8")
            errors = validator.validate(root)
            self.assertTrue(any("unexpected canonical path" in error for error in errors), errors)
            (root / ".env").unlink()
            module = root / "references" / "courses" / "ctis151.md"
            text = module.read_text(encoding="utf-8")
            module.write_text(text.replace("## Teaching posture\n\n", "## Teaching posture\n\n## ", 1), encoding="utf-8")
            errors = validator.validate(root)
            self.assertTrue(any("empty section Teaching posture" in error for error in errors), errors)

    def test_source_contains_no_raw_assets(self) -> None:
        self.assertFalse((SOURCE / "assets").exists())
        for path in _source_files():
            with self.subTest(path=path):
                self.assertNotIn(path.suffix.lower(), FORBIDDEN_SUFFIXES)

    def test_temporary_archives_have_expected_roots_and_payloads(self) -> None:
        builder = self._load_builder()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_archive, plugin_archive = root / "ctis.skill", root / "ctis-plugin.zip"
            builder.build_packages_transactional(SOURCE, skill_archive, plugin_archive)
            skill_payload = _archive_payload(skill_archive, "ctis/")
            plugin_payload = _archive_payload(plugin_archive, "ctis-plugin/skills/ctis/")
            self.assertEqual({f"ctis/{name}" for name in CANONICAL_FILES}, {
                f"ctis/{name}" for name in skill_payload
            })
            self.assertEqual(
                {f"ctis-plugin/skills/ctis/{name}" for name in CANONICAL_FILES}
                | {"ctis-plugin/.codex-plugin/plugin.json"}
                | {f"ctis-plugin/commands/{name}" for name in COMMAND_FILES},
                set(_archive_payload(plugin_archive, "")),
            )
            source_payload = {
                path.relative_to(SOURCE).as_posix(): path.read_bytes()
                for path in _source_files()
            }
            self.assertEqual(source_payload, skill_payload)
            self.assertEqual(source_payload, plugin_payload)
            self.assertEqual(
                {name: (ROOT / "commands" / name).read_bytes() for name in sorted(COMMAND_FILES)},
                {
                    name.removeprefix("ctis-plugin/commands/"): data
                    for name, data in _archive_payload(plugin_archive, "").items()
                    if name.startswith("ctis-plugin/commands/")
                },
            )

    def test_builder_is_deterministic_and_uses_exact_allowlist(self) -> None:
        builder = self._load_builder()
        self.assertEqual(CANONICAL_FILES, set(builder.CANONICAL_FILES))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first_skill, first_plugin = root / "a.skill", root / "a.zip"
            second_skill, second_plugin = root / "b.skill", root / "b.zip"
            builder.build_packages_transactional(SOURCE, first_skill, first_plugin)
            builder.build_packages_transactional(SOURCE, second_skill, second_plugin)
            self.assertEqual(first_skill.read_bytes(), second_skill.read_bytes())
            self.assertEqual(first_plugin.read_bytes(), second_plugin.read_bytes())
            copied = root / "source"
            shutil.copytree(SOURCE, copied)
            (copied / ".cache").mkdir()
            (copied / ".cache" / "state.txt").write_text("private", encoding="utf-8")
            with self.assertRaises(ValueError):
                builder.iter_skill_files(copied)

    def test_builder_rolls_back_both_outputs_if_second_replace_fails(self) -> None:
        builder = self._load_builder()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_output, plugin_output = root / "ctis.skill", root / "ctis-plugin.zip"
            skill_output.write_bytes(b"original skill")
            plugin_output.write_bytes(b"original plugin")
            calls = 0

            def fail_second_replace(source, target):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected second replacement failure")
                os.replace(source, target)

            with self.assertRaises(OSError):
                builder.build_packages_transactional(
                    SOURCE, skill_output, plugin_output, replace=fail_second_replace
                )
            self.assertEqual(b"original skill", skill_output.read_bytes())
            self.assertEqual(b"original plugin", plugin_output.read_bytes())

    def test_plugin_manifest_uses_documented_prompt_array(self) -> None:
        builder = self._load_builder()
        prompt = builder.PLUGIN_MANIFEST["interface"]["defaultPrompt"]
        self.assertIsInstance(prompt, list)
        self.assertGreaterEqual(len(prompt), 1)
        self.assertLessEqual(len(prompt), 3)
        self.assertTrue(all(isinstance(item, str) and len(item) <= 128 for item in prompt))

    def test_agents_openai_yaml_contract(self) -> None:
        text = (SOURCE / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertRegex(text, r'(?m)^\s*display_name:\s*"[^"]+"\s*$')
        short = re.search(r'(?m)^\s*short_description:\s*"([^"]+)"\s*$', text)
        self.assertIsNotNone(short)
        self.assertGreaterEqual(len(short.group(1)), 25)
        self.assertLessEqual(len(short.group(1)), 64)
        prompt = re.search(r'(?m)^\s*default_prompt:\s*"([^"]+)"\s*$', text)
        self.assertIsNotNone(prompt)
        self.assertIn("$ctis", prompt.group(1))

    def test_no_placeholders_or_broken_relative_references(self) -> None:
        red_flags = re.compile(r"(?i)\b(TODO|TBD|PLACEHOLDER)\b")
        for path in _source_files():
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            with self.subTest(path=path):
                self.assertIsNone(red_flags.search(text))
            for target in re.findall(r"\((references/[^)#]+|scripts/[^)#]+)\)", text):
                resolved = SOURCE / target
                with self.subTest(path=path, target=target):
                    self.assertTrue(resolved.is_file(), f"broken reference {target} in {path}")

    def test_skill_local_validator_accepts_source(self) -> None:
        script = SOURCE / "scripts" / "validate_ctis_skill.py"
        self.assertTrue(script.is_file(), f"missing {script}")
        result = subprocess.run(
            [sys.executable, str(script), str(SOURCE)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()

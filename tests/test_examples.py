from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "examples"))

from audit_public_tree import audit_public_tree  # type: ignore[import-not-found]
from run_example_suite import (  # type: ignore[import-not-found]
    MAX_OUTPUT_BYTES,
    ExampleDeclarationError,
    find_runtime,
    run_examples,
)
from check_examples import check_ctis151  # type: ignore[import-not-found]


COURSES = {
    "CTIS151", "CTIS163", "CTIS164", "CTIS166", "CTIS255", "CTIS256",
    "CTIS259", "CTIS262", "CTIS264", "CTIS359", "CTIS411", "CTIS417", "CTIS465",
    "CTIS474",
}
RECORD_FIELDS = {
    "id", "courses", "prompt", "artifact_paths", "verify", "expected",
    "runtime_required", "instructor_refs",
}
CONTEXT_ONLY_ID = "efe-mert-sahinkoc-department-context"


def write_suite(root: Path, records: list[dict[str, object]]) -> None:
    examples = root / "examples"
    examples.mkdir(parents=True, exist_ok=True)
    (examples / "index.json").write_text(
        json.dumps({"schema_version": 1, "examples": records}), encoding="utf-8"
    )


def record(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "python-pass",
        "courses": ["CTIS264"],
        "prompt": "Check a deterministic synthetic example.",
        "artifact_paths": ["fixtures/note.txt"],
        "verify": ["python", "-c", "print('EXAMPLE_OK')"],
        "expected": "EXAMPLE_OK\n",
        "runtime_required": "python",
        "instructor_refs": [],
    }
    base.update(overrides)
    return base


class RepositoryExampleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads(
            (ROOT / "examples" / "index.json").read_text(encoding="utf-8")
        )
        cls.records = cls.index["examples"]
        people = json.loads(
            (ROOT / "docs" / "instructors.json").read_text(encoding="utf-8")
        )
        cls.people = [*people["instructors"], *people["specialists"]]

    def test_index_covers_exact_canonical_course_set(self) -> None:
        covered = {course for item in self.records for course in item["courses"]}
        self.assertEqual(COURSES, covered)

    def test_records_have_exact_schema_unique_ids_and_safe_declared_paths(self) -> None:
        self.assertEqual(1, self.index["schema_version"])
        ids = [item["id"] for item in self.records]
        self.assertEqual(len(ids), len(set(ids)))
        for item in self.records:
            self.assertEqual(RECORD_FIELDS, set(item))
            self.assertIsInstance(item["verify"], list)
            self.assertTrue(item["verify"])
            self.assertTrue(all(isinstance(arg, str) and arg for arg in item["verify"]))
            self.assertIsInstance(item["runtime_required"], str)
            self.assertTrue(item["runtime_required"])
            declared = item["artifact_paths"]
            self.assertEqual(len(declared), len(set(declared)))
            for relative in declared:
                path = Path(relative)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                candidate = ROOT / "examples" / path
                self.assertTrue(candidate.is_file(), relative)
                self.assertFalse(candidate.is_symlink(), relative)

    def test_every_attributed_person_has_one_truthful_example_reference(self) -> None:
        expected = {
            person["example_id"]
            for person in self.people
            if person["evidence_class"] != "department-context-only"
        }
        actual = {
            ref for item in self.records for ref in item["instructor_refs"]
        }
        self.assertEqual(expected, actual)
        for example_id in expected:
            matches = [item for item in self.records if item["id"] == example_id]
            self.assertEqual(1, len(matches), example_id)
            self.assertIn(example_id, matches[0]["instructor_refs"])

    def test_context_only_person_is_an_explicit_no_attribution_exception(self) -> None:
        context = next(person for person in self.people if person["example_id"] == CONTEXT_ONLY_ID)
        self.assertEqual([], context["courses"])
        self.assertEqual("department-context-only", context["evidence_class"])
        self.assertNotIn(
            CONTEXT_ONLY_ID,
            {ref for item in self.records for ref in item["instructor_refs"]},
        )

    def test_public_examples_are_clean_and_strict_available_suite_passes(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.splitlines()
        examples = [
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "examples").rglob("*")
            if path.is_file()
        ]
        self.assertEqual([], audit_public_tree(ROOT, [*tracked, *examples]))
        results = run_examples(ROOT, strict=True)
        self.assertTrue(results)
        self.assertFalse([result for result in results if not result.passed and not result.skipped])

    def test_examples_contain_no_private_state_or_course_copy_markers(self) -> None:
        forbidden = re.compile(
            r"\b(?:angry|anxious|emotion|feels|hidden thoughts?|personality|secretly|"
            r"thinks|kızgın|duygu|hissediyor|kişilik|gizlice|düşünüyor|assignment|"
            r"exam|midterm|student)\b",
            re.IGNORECASE,
        )
        matches: list[str] = []
        for path in (ROOT / "examples").rglob("*"):
            if path.is_file():
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    matches.append(f"binary artifact: {path.relative_to(ROOT)}")
                    continue
                if forbidden.search(text):
                    matches.append(path.relative_to(ROOT).as_posix())
        self.assertEqual([], matches)


class RunnerBehaviorTests(unittest.TestCase):
    def test_safe_c_static_checker_does_not_confuse_fgets_with_gets(self) -> None:
        check_ctis151()

    def make_root(self, records: list[dict[str, object]]) -> TemporaryDirectory[str]:
        temporary = TemporaryDirectory()
        root = Path(temporary.name)
        fixture = root / "examples" / "fixtures"
        fixture.mkdir(parents=True)
        (fixture / "note.txt").write_text("synthetic\n", encoding="utf-8")
        write_suite(root, records)
        return temporary

    def test_available_command_passes_only_on_exact_output(self) -> None:
        with self.make_root([record()]) as directory:
            result = run_examples(Path(directory), strict=True)[0]
        self.assertTrue(result.passed)
        self.assertFalse(result.skipped)
        self.assertEqual("verified", result.reason)

    def test_unavailable_declared_runtime_is_a_named_skip_not_a_pass(self) -> None:
        missing = "ctis-runtime-that-does-not-exist"
        with self.make_root([record(runtime_required=missing)]) as directory:
            result = run_examples(Path(directory), strict=True)[0]
        self.assertFalse(result.passed)
        self.assertTrue(result.skipped)
        self.assertEqual(f"runtime unavailable: {missing}", result.reason)

    def test_available_nonzero_exit_is_a_failure(self) -> None:
        failing = record(verify=["python", "-c", "raise SystemExit(7)"], expected="")
        with self.make_root([failing]) as directory:
            result = run_examples(Path(directory), strict=True)[0]
        self.assertFalse(result.passed)
        self.assertFalse(result.skipped)
        self.assertIn("exit code 7", result.reason)

    def test_missing_undeclared_command_is_a_failure_not_a_skip(self) -> None:
        undeclared = record(
            verify=["ctis-command-that-does-not-exist", "--version"],
            runtime_required="python",
        )
        with self.make_root([undeclared]) as directory:
            result = run_examples(Path(directory), strict=True)[0]
        self.assertFalse(result.passed)
        self.assertFalse(result.skipped)
        self.assertEqual(
            "undeclared runtime unavailable: ctis-command-that-does-not-exist",
            result.reason,
        )

    def test_output_mismatch_is_a_failure(self) -> None:
        with self.make_root([record(expected="WRONG\n")]) as directory:
            result = run_examples(Path(directory), strict=True)[0]
        self.assertFalse(result.passed)
        self.assertIn("output mismatch", result.reason)

    def test_timeout_is_bounded_and_reported(self) -> None:
        slow = record(
            verify=["python", "-c", "import time; time.sleep(20)"], expected=""
        )
        with self.make_root([slow]) as directory:
            with patch("run_example_suite.COMMAND_TIMEOUT_SECONDS", 0.05):
                result = run_examples(Path(directory), strict=True)[0]
        self.assertFalse(result.passed)
        self.assertIn("timed out", result.reason)

    def test_output_is_bounded_and_excess_is_a_failure(self) -> None:
        loud = record(
            verify=["python", "-c", f"print('x'*{MAX_OUTPUT_BYTES + 10})"],
            expected="",
        )
        with self.make_root([loud]) as directory:
            result = run_examples(Path(directory), strict=True)[0]
        self.assertFalse(result.passed)
        self.assertLessEqual(len(result.output.encode("utf-8")), MAX_OUTPUT_BYTES)
        self.assertIn("output limit", result.reason)

    def test_malformed_or_unsafe_declarations_raise_before_execution(self) -> None:
        unsafe_cases = (
            record(artifact_paths=["../outside.txt"]),
            record(artifact_paths=[str(Path.cwd().resolve() / "outside.txt")]),
            record(verify="python -c print(1)"),
            record(verify=["python", "-c", "print(1)", ">", "out.txt"]),
            record(verify=["python", "-c", "print(1)", "2>out.txt"]),
            record(verify=["python", "-c", "print($(whoami))"]),
            record(artifact_paths=["fixtures/note.txt", "fixtures/note.txt"]),
        )
        for unsafe in unsafe_cases:
            with self.subTest(unsafe=unsafe):
                with self.make_root([unsafe]) as directory:
                    with self.assertRaises(ExampleDeclarationError):
                        run_examples(Path(directory), strict=True)

    def test_malformed_schema_fields_are_rejected(self) -> None:
        malformed_cases = (
            record(courses=[]),
            record(courses=["CTIS999"]),
            record(runtime_required="../python"),
            record(instructor_refs=["same", "same"]),
            record(expected=7),
        )
        for malformed in malformed_cases:
            with self.subTest(malformed=malformed):
                with self.make_root([malformed]) as directory:
                    with self.assertRaises(ExampleDeclarationError):
                        run_examples(Path(directory), strict=True)

    def test_symlink_artifact_is_rejected(self) -> None:
        with self.make_root([record()]) as directory:
            root = Path(directory)
            artifact = root / "examples" / "fixtures" / "note.txt"
            original_is_symlink = Path.is_symlink

            def report_artifact_link(candidate: Path) -> bool:
                return candidate == artifact or original_is_symlink(candidate)

            with patch.object(
                Path, "is_symlink", autospec=True, side_effect=report_artifact_link
            ):
                with self.assertRaises(ExampleDeclarationError):
                    run_examples(root, strict=True)

    def test_duplicate_ids_are_rejected_but_shared_read_only_artifacts_are_allowed(self) -> None:
        with self.make_root([record(), record()]) as directory:
            with self.assertRaises(ExampleDeclarationError):
                run_examples(Path(directory), strict=True)

        with self.make_root([record(), record(id="other")]) as directory:
            results = run_examples(Path(directory), strict=True)
        self.assertTrue(all(result.passed for result in results))

    def test_runtime_probe_rejects_a_nonworking_path_and_accepts_git_bash_fallback(self) -> None:
        with TemporaryDirectory() as directory:
            fake = Path(directory) / ("bash.exe" if os.name == "nt" else "bash")
            fake.write_text("not executable", encoding="utf-8")
            if os.name != "nt":
                fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            with patch("run_example_suite.shutil.which", return_value=str(fake)):
                with patch("run_example_suite._git_bash_candidates", return_value=[]):
                    self.assertIsNone(find_runtime("bash"))

        git_bash = Path("C:" + "/Program Files/Git/bin/bash.exe")
        if os.name == "nt" and git_bash.is_file():
            with patch("run_example_suite.shutil.which", return_value=None):
                self.assertEqual(git_bash, Path(find_runtime("bash") or ""))


if __name__ == "__main__":
    unittest.main()

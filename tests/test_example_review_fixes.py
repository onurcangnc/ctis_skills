from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "tools"))

from check_examples import (  # type: ignore[import-not-found]
    validate_ctis262,
    validate_ctis359,
    validate_ctis411,
    validate_ctis474,
)
from run_example_suite import (  # type: ignore[import-not-found]
    ExampleDeclarationError,
    _safe_manifest_relative,
    _validate_command,
)


def load_example(relative: str) -> dict[str, object]:
    return json.loads((ROOT / "examples" / relative).read_text(encoding="utf-8"))


class CrossPlatformPathBoundaryTests(unittest.TestCase):
    def test_artifact_classifier_rejects_every_root_drive_anchor_and_traversal(self) -> None:
        unsafe = (
            "\\" + "Windows\\System32\\cmd.exe",
            "\\" + "Users\\public\\outside.py",
            "C:" + "relative-on-drive.py",
            "C:" + "\\absolute\\outside.py",
            "\\" + "\\server\\share\\outside.py",
            "\\" + "\\?\\C:\\device\\outside.py",
            "/" + "var/tmp/outside.py",
            "../outside.py",
            "safe/../../outside.py",
        )
        for value in unsafe:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ExampleDeclarationError, "relative path"):
                    _safe_manifest_relative(value, "artifact")

    def test_command_classifier_rejects_windows_root_and_drive_relative_arguments(self) -> None:
        unsafe = (
            "\\" + "Windows\\System32\\cmd.exe",
            "\\" + "Users\\public\\outside.py",
            "C:" + "outside.py",
        )
        for value in unsafe:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ExampleDeclarationError, "relative path"):
                    _validate_command(["python", value], "verify")

    def test_classifier_accepts_only_portable_relative_manifest_paths(self) -> None:
        self.assertEqual(Path("ctis264/merge_ranges.py"), _safe_manifest_relative("ctis264/merge_ranges.py", "artifact"))
        self.assertEqual(
            ["python", "check_examples.py", "CTIS264"],
            _validate_command(["python", "check_examples.py", "CTIS264"], "verify"),
        )


class SemanticMutationTests(unittest.TestCase):
    def test_ctis359_requires_definitions_exact_citations_and_valid_links(self) -> None:
        original = load_example("ctis359/analysis.json")
        validate_ctis359(original)

        mutations = []
        missing_definitions = copy.deepcopy(original)
        missing_definitions.pop("definitions")
        mutations.append(missing_definitions)
        missing_citations = copy.deepcopy(original)
        missing_citations.pop("citations")
        mutations.append(missing_citations)
        broken_citation = copy.deepcopy(original)
        broken_citation["definitions"]["branch_coverage"]["citation_ids"] = ["BROKEN-ID"]
        mutations.append(broken_citation)
        wrong_url = copy.deepcopy(original)
        wrong_url["citations"][0]["url"] = "https://example.test/not-primary"
        mutations.append(wrong_url)

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises((AssertionError, KeyError, TypeError)):
                    validate_ctis359(mutation)

    def test_ctis262_rejects_address_and_evidence_link_mutations(self) -> None:
        original = load_example("ctis262/topology.json")
        validate_ctis262(original)

        outside_subnet = copy.deepcopy(original)
        outside_subnet["endpoints"][0]["address"] = "203.0.113.10/28"
        broken_gateway = copy.deepcopy(original)
        broken_gateway["endpoints"][0]["gateway"] = "not-an-address"
        missing_route = copy.deepcopy(original)
        next(item for item in missing_route["evidence"] if item["check"] == "primary-link-down")["route"] = "ROUTE-MISSING"
        missing_endpoint = copy.deepcopy(original)
        missing_endpoint["evidence"][0]["target"] = "unknown-endpoint"
        wrong_same_vlan_outcome = copy.deepcopy(original)
        next(
            item
            for item in wrong_same_vlan_outcome["evidence"]
            if item["check"] == "same-vlan"
        )["expected"] = "unreachable"
        wrong_inter_vlan_outcome = copy.deepcopy(original)
        next(
            item
            for item in wrong_inter_vlan_outcome["evidence"]
            if item["check"] == "inter-vlan"
        )["expected"] = "unreachable-via-backup"

        for mutation in (
            outside_subnet,
            broken_gateway,
            missing_route,
            missing_endpoint,
            wrong_same_vlan_outcome,
            wrong_inter_vlan_outcome,
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaises((AssertionError, KeyError, TypeError, ValueError)):
                    validate_ctis262(mutation)

    def test_ctis411_rejects_unstable_ids_broken_links_and_incomplete_traceability(self) -> None:
        original = load_example("ctis411/project.json")
        validate_ctis411(original)

        unstable_id = copy.deepcopy(original)
        unstable_id["requirements"][0]["id"] = "requirement-one"
        unstable_id["work"][0]["requirement"] = "requirement-one"
        unstable_id["verifications"][0]["requirement"] = "requirement-one"
        unstable_id["traceability"][0]["requirement"] = "requirement-one"
        missing_verification = copy.deepcopy(original)
        missing_verification["verifications"].pop()
        incomplete = copy.deepcopy(original)
        incomplete["traceability"].pop()
        broken_work_link = copy.deepcopy(original)
        broken_work_link["traceability"][0]["work"] = "WBS-999"

        for mutation in (unstable_id, missing_verification, incomplete, broken_work_link):
            with self.subTest(mutation=mutation):
                with self.assertRaises((AssertionError, KeyError, TypeError, ValueError)):
                    validate_ctis411(mutation)

    def test_ctis474_rejects_mismatched_criteria_dates_evidence_and_links(self) -> None:
        original = load_example("ctis474/audit.json")
        validate_ctis474(original)

        criterion_mismatch = copy.deepcopy(original)
        criterion_mismatch["findings"][0]["criteria"] = "POL-OTHER"
        bad_date = copy.deepcopy(original)
        bad_date["findings"][0]["target_date"] = "2026-02-30"
        missing_question = copy.deepcopy(original)
        missing_question["findings"][0]["question"] = "Q-999"
        empty_evidence = copy.deepcopy(original)
        empty_evidence["findings"][0]["evidence"] = ""

        for mutation in (criterion_mismatch, bad_date, missing_question, empty_evidence):
            with self.subTest(mutation=mutation):
                with self.assertRaises((AssertionError, KeyError, TypeError, ValueError)):
                    validate_ctis474(mutation)


if __name__ == "__main__":
    unittest.main()

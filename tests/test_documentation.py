from __future__ import annotations

import hashlib
import json
import re
import unittest
import zipfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
INSTALL = ROOT / "INSTALL.md"
DISCLOSURE = ROOT / "DISCLOSURE.md"
NOTICE = ROOT / "NOTICE.md"
LICENSE = ROOT / "LICENSE"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
SECURITY = ROOT / "SECURITY.md"
COLLABORATE = ROOT / "COLLABORATE.md"

COURSES = (
    "CTIS151", "CTIS163", "CTIS164", "CTIS166", "CTIS255", "CTIS256",
    "CTIS259", "CTIS262", "CTIS264", "CTIS359", "CTIS411", "CTIS465",
    "CTIS474",
)
PACKAGE_MEMBERS = {
    "ctis.skill": 18,
    "ctis-codex-plugin.zip": 32,
    "ctis-claude-plugin.zip": 33,
}
EXACT_COMMANDS = (
    "claude plugin marketplace add onurcangnc/ctis_skills",
    "claude plugin install ctis@ctis-skills",
    "claude plugin marketplace update ctis-skills",
    "claude plugin update ctis@ctis-skills",
    "claude plugin uninstall ctis@ctis-skills",
    "codex plugin marketplace add onurcangnc/ctis_skills --ref main",
    "codex plugin add ctis@ctis-skills",
    "codex plugin marketplace upgrade ctis-skills",
    "codex plugin remove ctis@ctis-skills",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.people_manifest = json.loads(_text(ROOT / "docs" / "instructors.json"))
        cls.people = [
            *cls.people_manifest["instructors"],
            *cls.people_manifest["specialists"],
        ]
        cls.examples = json.loads(_text(ROOT / "examples" / "index.json"))["examples"]
        cls.sources = json.loads(_text(ROOT / "docs" / "assets" / "sources.json"))["assets"]

    def test_required_documents_exist_and_readme_leads_with_outcome(self) -> None:
        for path in (README, INSTALL, DISCLOSURE, NOTICE, LICENSE, CONTRIBUTING, SECURITY, COLLABORATE):
            self.assertTrue(path.is_file(), path.name)
        readme = _text(README)
        self.assertRegex(
            readme,
            r'^# CTIS Skills\s+<a href="https://www\.ctis\.bilkent\.edu\.tr/">'
            r'<img src="docs/assets/bilkent-ctis-logo\.png"[^>]*></a>\s+'
            r'One CTIS skill with a command per course',
        )
        self.assertIn("same semantic behavior in Codex and Claude Code", readme)
        self.assertIn("run `cd examples` once", readme)
        self.assertNotRegex(readme, r"(?i)shields\.io|<img[^>]+badge|build status")

    def test_install_and_lifecycle_commands_are_exact(self) -> None:
        readme = _text(README)
        install = _text(INSTALL)
        for command in EXACT_COMMANDS[:2] + EXACT_COMMANDS[5:7]:
            self.assertEqual(1, readme.count(command), command)
        expected_install_counts = {command: 1 for command in EXACT_COMMANDS}
        expected_install_counts["codex plugin add ctis@ctis-skills"] = 2
        expected_install_counts["codex plugin remove ctis@ctis-skills"] = 2
        for command, expected_count in expected_install_counts.items():
            self.assertEqual(expected_count, install.count(command), command)
        self.assertEqual(1, readme.count("`/ctis`"))
        self.assertEqual(1, readme.count("`$ctis`"))
        for topic in (
            "Requirements", "Verify and invoke", "Update", "Uninstall",
            "Installing from local packages", "Troubleshooting",
        ):
            self.assertIn(topic, install)
        for artifact in PACKAGE_MEMBERS:
            self.assertIn(artifact, install)

    def test_readme_has_exact_course_map_and_working_local_links(self) -> None:
        readme = _text(README)
        for course in COURSES:
            module = f"skills/ctis/references/courses/{course.casefold()}.md"
            self.assertRegex(
                readme,
                rf"(?m)^\| \[{course}\]\({re.escape(module)}\) \| .+ \| \[.+\]\(examples/[^)]+\) \|$",
            )
        course_rows = re.findall(r"(?m)^\| \[CTIS\d{3}\]\(", readme)
        self.assertEqual(13, len(course_rows))

    def test_readme_carries_no_instructor_or_specialist_profiles(self) -> None:
        readme = _text(README)
        self.assertEqual(12, len(self.people_manifest["instructors"]))
        self.assertEqual(4, len(self.people_manifest["specialists"]))
        for phrase in (
            "Observable communications and decision patterns",
            "Persons with course contributions",
            "Specialist, laboratory, and department context",
            "Direct observation",
            "Conservative association",
            "Private state unknown",
            "anonymous and shared capabilities",
            "official CTIS portrait",
        ):
            self.assertNotIn(phrase, readme)

        self.assertNotRegex(readme, r'<details id="profile-')
        self.assertNotRegex(readme, r"<summary><strong>")
        for person in self.people:
            self.assertNotIn(person["name"], readme, person["name"])
            self.assertNotIn(Path(person["image"]).stem, readme, person["name"])

    def test_unattributed_examples_render_exact_prompt_argv_expected_and_result_truth(self) -> None:
        readme = _text(README)
        by_id = {record["id"]: record for record in self.examples}
        self.assertEqual(23, len(by_id))
        attributed_ids = {
            record["id"] for record in self.examples if record["instructor_refs"]
        }
        self.assertEqual(15, len(attributed_ids))
        unattributed_ids = sorted(set(by_id) - attributed_ids)
        self.assertEqual(8, len(unattributed_ids))
        for example_id in unattributed_ids:
            record = by_id[example_id]
            self.assertEqual(1, readme.count(example_id), example_id)
            self.assertIn(record["prompt"], readme)
            self.assertIn(" ".join(record["verify"]), readme)
            self.assertIn(json.dumps(record["expected"], ensure_ascii=False), readme)

        self.assertIn("22 PASS / 1 SKIP (PHP runtime unavailable) / 0 FAIL", readme)
        self.assertNotIn("23 PASS", readme)

    def test_release_summary_matches_current_packages_and_manifests(self) -> None:
        readme = _text(README)
        self.assertIn("Codex: 18 canonical skill files", readme)
        self.assertIn("Claude: 17 semantic files", readme)
        self.assertIn("only `agents/openai.yaml` is dropped", readme)
        for artifact, expected_members in PACKAGE_MEMBERS.items():
            path = ROOT / "dist" / artifact
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with zipfile.ZipFile(path) as archive:
                members = [name for name in archive.namelist() if not name.endswith("/")]
            self.assertEqual(expected_members, len(members))
            self.assertIn(f"`{artifact}`", readme)
            self.assertIn(f"`{digest}`", readme)
            self.assertRegex(readme, rf"`{re.escape(artifact)}` \| {expected_members} \|")
        for manifest in (
            ".codex-plugin/plugin.json", ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json", "plugin.json",
        ):
            self.assertIn(manifest, readme)
        self.assertIn("ctis@ctis-skills", readme)

    def test_testing_guide_release_hashes_match_the_tracked_packages(self) -> None:
        testing = _text(ROOT / "docs" / "TESTING.md")
        for artifact, expected_members in PACKAGE_MEMBERS.items():
            digest = hashlib.sha256((ROOT / "dist" / artifact).read_bytes()).hexdigest()
            self.assertRegex(
                testing,
                rf"`{re.escape(artifact)}` \| {expected_members} \| `{digest}` \|",
            )

    def test_disclosure_covers_non_harm_private_state_and_decision_boundaries(self) -> None:
        disclosure = _text(DISCLOSURE).casefold()
        required = (
            "independent, unofficial", "approved or endorsed",
            "software-assistance", "harm", "rank", "imitate", "discredit",
            "surveil", "target", "private emotions", "thoughts", "communications",
            "records", "non-public systems", "public systems",
            "confidence", "academic", "disciplinary", "psychological", "legal",
            "administrative decisions", "academic integrity",
            "source verification", "safe use", "repository issues",
        )
        for phrase in required:
            self.assertIn(phrase, disclosure)
        readme = _text(README)
        self.assertIn("[disclosure notice](DISCLOSURE.md)", readme)
        self.assertIn("independent, unofficial", readme.casefold())

    def test_contributing_binds_anonymity_official_sources_and_acceptance(self) -> None:
        contributing = _text(CONTRIBUTING)
        for phrase in (
            "distributed skill text is anonymous",
            "No person name",
            "`skills/ctis`",
            "https://*.bilkent.edu.tr",
            "docs/assets/sources.json",
            "python -B tools/run_acceptance.py",
            "python -B tools/audit_public_tree.py --tracked",
            "ACCEPTANCE_OK",
            "tools/build_ctis_packages.py",
        ):
            self.assertIn(phrase, contributing)
        self.assertIn("[the disclosure notice](DISCLOSURE.md)", contributing)
        self.assertIn("[docs/TESTING.md](docs/TESTING.md)", contributing)

    def test_security_gives_a_private_channel_without_personal_contact_data(self) -> None:
        security = _text(SECURITY)
        for phrase in (
            "Report a vulnerability",
            "public issue",
            "7 days",
            "30 days",
            "Out of scope",
            "independent, unofficial",
        ):
            self.assertIn(phrase, security)
        self.assertIn("[README.md](README.md)", security)
        self.assertNotRegex(security, r"[\w.+-]+@[\w-]+\.[\w.]+")
        self.assertNotRegex(security, r"(?i)\+\d[\d ()-]{7,}")

    def test_notice_and_license_keep_third_party_assets_outside_mit(self) -> None:
        notice = _text(NOTICE)
        license_text = _text(LICENSE)
        self.assertIn("not licensed under the MIT License", notice)
        self.assertIn("Bilkent University", notice)
        self.assertIn("no license or endorsement is implied", notice.casefold())
        self.assertIn("docs/assets/sources.json", notice)
        self.assertIn("repository issues", notice.casefold())
        for asset in self.sources:
            self.assertIn(asset["path"], notice)
            self.assertIn(asset["source_page"], notice)
            self.assertIn(asset["source_url"], notice)
        self.assertIn("MIT License", license_text)
        self.assertIn("original code and text", license_text)
        self.assertIn("Third-party marks and images are excluded", license_text)

    def test_all_relative_links_resolve_and_official_links_are_well_formed(self) -> None:
        local_links: list[tuple[Path, str]] = []
        external_links: list[str] = []
        for document in (README, INSTALL, DISCLOSURE, NOTICE, CONTRIBUTING, SECURITY, COLLABORATE):
            text = _text(document)
            targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
            targets += re.findall(r'(?:href|src)="([^"]+)"', text)
            for target in targets:
                if target.startswith(("https://", "http://")):
                    external_links.append(target)
                elif not target.startswith("#"):
                    local_links.append((document, target))
        for document, target in local_links:
            relative = target.split("#", 1)[0]
            self.assertTrue((document.parent / relative).is_file(), f"{document.name}: {target}")
        for target in external_links:
            parsed = urlparse(target)
            self.assertEqual("https", parsed.scheme, target)
            self.assertTrue(parsed.netloc, target)
        official = [url for url in external_links if "bilkent.edu.tr" in urlparse(url).netloc]
        self.assertTrue(official)
        self.assertTrue(all(urlparse(url).netloc.endswith("bilkent.edu.tr") for url in official))

    def test_documents_avoid_hype_private_state_claims_local_paths_and_slop(self) -> None:
        corpus = "\n".join(
            _text(path)
            for path in (README, INSTALL, DISCLOSURE, NOTICE, CONTRIBUTING, SECURITY, COLLABORATE)
        )
        banned_slop = (
            "delve", "foster", "leverage", "utilize", "facilitate", "empower",
            "streamline", "robust", "cutting-edge", "paradigm shift", "game changer",
            "tapestry", "realm", "beacon", "multifaceted", "meticulous", "intricate",
            "paramount", "transformative", "elevate", "embark", "supercharge",
            "harness", "ever-evolving", "let's dive in", "in conclusion",
        )
        lowered = corpus.casefold()
        self.assertEqual([], [term for term in banned_slop if term in lowered])
        self.assertNotRegex(
            lowered,
            r"\b(?:is|feels|seems) (?:angry|anxious)|(?:secretly|privately) thinks|"
            r"(?:kızgın|kaygılı)dır|gizlice düşünür|kişilik profili",
        )
        user_root = "/" + "Users" + "/"
        unix_home_root = "/" + "home" + "/"
        self.assertNotRegex(
            corpus,
            rf"(?i)\b[A-Z]:[\\/]|{re.escape(user_root)}|"
            rf"{re.escape(unix_home_root)}[^ /]+/",
        )
        self.assertNotIn("—", corpus)


if __name__ == "__main__":
    unittest.main()

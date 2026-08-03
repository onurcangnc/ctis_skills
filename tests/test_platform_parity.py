from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


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


def _load_payloads_module():
    path = ROOT / "tools" / "platform_payloads.py"
    spec = importlib.util.spec_from_file_location("platform_payloads", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PlatformParityTests(unittest.TestCase):
    def test_adapters_preserve_exact_semantic_payload_bytes(self) -> None:
        payloads = _load_payloads_module()
        codex = payloads.codex_skill_payload(SOURCE)
        claude = payloads.claude_skill_payload(SOURCE)

        self.assertEqual(CANONICAL_FILES, set(codex))
        self.assertEqual(SEMANTIC_FILES, set(claude))
        self.assertNotIn("agents/openai.yaml", claude)
        self.assertEqual((SOURCE / "agents" / "openai.yaml").read_bytes(), codex["agents/openai.yaml"])
        for relative in sorted(SEMANTIC_FILES):
            expected = (SOURCE / relative).read_bytes()
            with self.subTest(relative=relative):
                self.assertEqual(expected, codex[relative])
                self.assertEqual(expected, claude[relative])

    def test_adapters_publish_exactly_the_same_semantic_mapping(self) -> None:
        payloads = _load_payloads_module()
        codex = payloads.codex_skill_payload(SOURCE)
        claude = payloads.claude_skill_payload(SOURCE)

        self.assertEqual(
            {relative: codex[relative] for relative in SEMANTIC_FILES},
            claude,
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "tools" / "validate_platform_manifests.py"
    spec = importlib.util.spec_from_file_location("validate_platform_manifests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PlatformManifestTests(unittest.TestCase):
    def test_claude_marketplace_points_to_root_plugin(self) -> None:
        validator = _load_validator()

        self.assertEqual([], validator.validate_claude(ROOT))

    def test_codex_manifest_points_to_shared_skill(self) -> None:
        validator = _load_validator()

        self.assertEqual([], validator.validate_codex(ROOT))

    def test_manifest_names_and_urls_are_consistent(self) -> None:
        validator = _load_validator()

        self.assertEqual([], validator.validate_all(ROOT))

        with (ROOT / ".codex-plugin" / "plugin.json").open(encoding="utf-8") as stream:
            codex = json.load(stream)
        with (ROOT / ".claude-plugin" / "plugin.json").open(encoding="utf-8") as stream:
            claude = json.load(stream)

        self.assertEqual("ctis", claude["name"])
        self.assertEqual(claude["name"], codex["name"])
        self.assertEqual("https://github.com/onurcangnc/ctis_skills", codex["repository"])

    def test_validator_rejects_wrong_marketplace_or_skill_path(self) -> None:
        validator = _load_validator()
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for relative in (
                ".claude-plugin/marketplace.json",
                ".claude-plugin/plugin.json",
                ".codex-plugin/plugin.json",
                "plugin.json",
                "skills/ctis/SKILL.md",
            ):
                source = ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())

            marketplace_path = root / ".claude-plugin" / "marketplace.json"
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            marketplace["plugins"][0]["source"] = "./plugin"
            marketplace_path.write_text(json.dumps(marketplace), encoding="utf-8")

            codex_path = root / ".codex-plugin" / "plugin.json"
            codex = json.loads(codex_path.read_text(encoding="utf-8"))
            codex["skills"] = "./other-skills/"
            codex_path.write_text(json.dumps(codex), encoding="utf-8")

            errors = validator.validate_all(root)

        self.assertIn("Claude marketplace plugin source must be './'", errors)
        self.assertIn("Codex skills must be './skills/'", errors)

    def test_no_manifest_contains_instructor_identity(self) -> None:
        forbidden = (ROOT / "tests" / "forbidden-identifiers.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        manifests = (
            ROOT / ".claude-plugin" / "marketplace.json",
            ROOT / ".claude-plugin" / "plugin.json",
            ROOT / ".codex-plugin" / "plugin.json",
            ROOT / "plugin.json",
        )

        content = "\n".join(path.read_text(encoding="utf-8").casefold() for path in manifests)

        for identity in forbidden:
            with self.subTest(identity=identity):
                self.assertNotIn(identity.casefold(), content)


if __name__ == "__main__":
    unittest.main()

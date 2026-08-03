"""Validate the Claude Code and Codex metadata for this shared skill tree."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:  # imported as a package by the test suite
    from tools.release_version import release_version
except ModuleNotFoundError:  # run as a script, with tools/ on sys.path
    from release_version import release_version


REPOSITORY_URL = "https://github.com/onurcangnc/ctis_skills"
PLUGIN_NAME = "ctis"
MARKETPLACE_NAME = "ctis-skills"
VERSION = release_version()
PUBLISHER = "CTIS Skills Contributors"
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\."
    r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
ASSET_FIELDS = {"composerIcon", "logo", "logoDark", "screenshots"}


def validate_claude(root: Path) -> list[str]:
    """Return deterministic contract violations for the Claude Code manifests."""
    root = root.resolve()
    errors: list[str] = []
    marketplace = _load_object(root / ".claude-plugin" / "marketplace.json", "Claude marketplace", errors)
    plugin = _load_object(root / ".claude-plugin" / "plugin.json", "Claude plugin", errors)

    if marketplace is not None:
        _expect_equal(errors, marketplace.get("$schema"), "https://www.schemastore.org/claude-code-marketplace.json", "Claude marketplace schema")
        _expect_equal(errors, marketplace.get("name"), MARKETPLACE_NAME, "Claude marketplace name")
        _expect_equal(errors, marketplace.get("description"), "Course-routed CTIS coding and verification skills.", "Claude marketplace description")
        owner = marketplace.get("owner")
        _expect_equal(errors, owner.get("name") if isinstance(owner, dict) else None, PUBLISHER, "Claude marketplace owner name")
        plugins = marketplace.get("plugins")
        if not isinstance(plugins, list) or len(plugins) != 1 or not isinstance(plugins[0], dict):
            errors.append("Claude marketplace must contain exactly one plugin")
        else:
            entry = plugins[0]
            _expect_equal(errors, entry.get("name"), PLUGIN_NAME, "Claude marketplace plugin name")
            _expect_equal(errors, entry.get("source"), "./", "Claude marketplace plugin source")
            _expect_equal(errors, entry.get("category"), "education", "Claude marketplace plugin category")
            _expect_equal(errors, entry.get("description"), "Apply anonymous CTIS course patterns to coding, reasoning, and verification.", "Claude marketplace plugin description")

    if plugin is not None:
        _expect_equal(errors, plugin.get("name"), PLUGIN_NAME, "Claude plugin name")
        _expect_equal(errors, plugin.get("version"), VERSION, "Claude plugin version")
        _require_semver(errors, plugin.get("version"), "Claude plugin version")
        _require_non_empty(errors, plugin.get("description"), "Claude plugin description")
        _validate_author(errors, plugin.get("author"), "Claude plugin author")
    return sorted(set(errors))


def validate_codex(root: Path) -> list[str]:
    """Return deterministic contract violations for the Codex and generic manifests."""
    root = root.resolve()
    errors: list[str] = []
    plugin = _load_object(root / ".codex-plugin" / "plugin.json", "Codex plugin", errors)
    generic = _load_object(root / "plugin.json", "Generic plugin", errors)

    if generic is not None:
        _expect_equal(errors, generic.get("name"), PLUGIN_NAME, "Generic plugin name")
        _require_non_empty(errors, generic.get("description"), "Generic plugin description")

    if plugin is None:
        return sorted(set(errors))
    _expect_equal(errors, plugin.get("name"), PLUGIN_NAME, "Codex plugin name")
    _expect_equal(errors, plugin.get("version"), VERSION, "Codex plugin version")
    _require_semver(errors, plugin.get("version"), "Codex plugin version")
    _require_non_empty(errors, plugin.get("description"), "Codex plugin description")
    _validate_author(errors, plugin.get("author"), "Codex plugin author")
    for field in ("homepage", "repository"):
        _require_https(errors, plugin.get(field), f"Codex {field}")
    _expect_equal(errors, plugin.get("repository"), REPOSITORY_URL, "Codex repository")
    _expect_equal(errors, plugin.get("license"), "MIT", "Codex license")
    keywords = plugin.get("keywords")
    if not isinstance(keywords, list) or not keywords or not all(isinstance(item, str) and item.strip() for item in keywords):
        errors.append("Codex keywords must be a non-empty array of strings")
    _expect_equal(errors, plugin.get("skills"), "./skills/", "Codex skills")
    if not (root / "skills" / "ctis" / "SKILL.md").is_file():
        errors.append("Canonical skill must exist at skills/ctis/SKILL.md")

    interface = plugin.get("interface")
    if not isinstance(interface, dict):
        errors.append("Codex interface must be an object")
        return sorted(set(errors))
    _expect_equal(errors, interface.get("displayName"), "CTIS Skills", "Codex interface displayName")
    short_description = interface.get("shortDescription")
    if not isinstance(short_description, str) or not 25 <= len(short_description) <= 64:
        errors.append("Codex interface shortDescription must contain 25 to 64 characters")
    _require_non_empty(errors, interface.get("longDescription"), "Codex interface longDescription")
    _expect_equal(errors, interface.get("developerName"), PUBLISHER, "Codex interface developerName")
    _expect_equal(errors, interface.get("category"), "Education", "Codex interface category")
    _expect_equal(errors, interface.get("capabilities"), ["Instructions"], "Codex interface capabilities")
    _expect_equal(errors, interface.get("websiteURL"), REPOSITORY_URL, "Codex interface websiteURL")
    _require_https(errors, interface.get("websiteURL"), "Codex interface websiteURL")
    _validate_prompts(errors, interface.get("defaultPrompt"))
    for field in sorted(ASSET_FIELDS & set(interface)):
        errors.append(f"Codex interface must not reference unsupported asset field {field}")
    return sorted(set(errors))


def validate_all(root: Path) -> list[str]:
    """Validate every distribution manifest without external tool dependencies."""
    return sorted(set(validate_claude(root) + validate_codex(root)))


def _load_object(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"{label} manifest is missing: {path.as_posix()}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append(f"{label} manifest must contain valid JSON")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label} manifest must contain an object")
        return None
    return payload


def _expect_equal(errors: list[str], actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        errors.append(f"{label} must be {expected!r}")


def _require_non_empty(errors: list[str], value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")


def _require_semver(errors: list[str], value: Any, label: str) -> None:
    if not isinstance(value, str) or SEMVER_RE.fullmatch(value) is None:
        errors.append(f"{label} must be strict semver")


def _require_https(errors: list[str], value: Any, label: str) -> None:
    parsed = urlparse(value) if isinstance(value, str) else None
    if parsed is None or parsed.scheme != "https" or not parsed.netloc:
        errors.append(f"{label} must be an HTTPS URL")


def _validate_author(errors: list[str], value: Any, label: str) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return
    _expect_equal(errors, value.get("name"), PUBLISHER, f"{label} name")
    _expect_equal(errors, value.get("url"), REPOSITORY_URL, f"{label} URL")
    _require_https(errors, value.get("url"), f"{label} URL")


def _validate_prompts(errors: list[str], prompts: Any) -> None:
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
        errors.append("Codex interface defaultPrompt must contain one to three prompts")
        return
    for index, prompt in enumerate(prompts):
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 128 or "$ctis" not in prompt:
            errors.append(f"Codex interface defaultPrompt[{index}] must use $ctis and contain at most 128 characters")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate shared Claude Code and Codex manifests.")
    parser.add_argument("root", type=Path, nargs="?", default=Path.cwd())
    arguments = parser.parse_args()
    errors = validate_all(arguments.root)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Platform manifests validated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

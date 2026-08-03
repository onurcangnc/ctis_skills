from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


APPROVED_ROOTS = {
    ".claude-plugin",
    "commands",
    ".codex-plugin",
    "docs",
    "dist",
    "examples",
    "skills",
    "tests",
    "tools",
}
APPROVED_ROOT_FILES = {
    ".gitattributes",
    ".gitignore",
    "CONTRIBUTING.md",
    "DISCLOSURE.md",
    "INSTALL.md",
    "LICENSE",
    "NOTICE.md",
    "README.md",
    "requirements-dev.txt",
    "SECURITY.md",
    "plugin.json",
}
FORBIDDEN_SUFFIXES = {
    ".7z",
    ".apk",
    ".bin",
    ".bz2",
    ".cap",
    ".class",
    ".com",
    ".db",
    ".dll",
    ".dmg",
    ".doc",
    ".docm",
    ".docx",
    ".exe",
    ".gz",
    ".iso",
    ".jar",
    ".key",
    ".mdb",
    ".msi",
    ".odb",
    ".odg",
    ".odp",
    ".ods",
    ".odt",
    ".pcap",
    ".pcapng",
    ".pdf",
    ".pem",
    ".pfx",
    ".p12",
    ".ppt",
    ".pptm",
    ".pptx",
    ".pyc",
    ".pyo",
    ".rar",
    ".sqlite",
    ".sqlite3",
    ".skill",
    ".tar",
    ".war",
    ".xls",
    ".xlsm",
    ".xlsx",
    ".xz",
    ".zip",
}
ALLOWED_RELEASE_ARCHIVES = {
    "dist/ctis.skill",
    "dist/ctis-claude-plugin.zip",
    "dist/ctis-codex-plugin.zip",
}
IMAGE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
CACHE_DIRECTORIES = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"\b(?:[a-z][a-z0-9]*_)*(?:api[_-]?key|access[_-]?key|auth(?:entication)?[_-]?token|"
    r"github[_-]?token|secret|token|password|passwd|credentials?)\s*(?:=|:)\s*[^\s#]+",
    re.IGNORECASE,
)
HOME_PATH_RE = re.compile(
    r"(?:[A-Z]:[\\/](?:users|documents and settings)[\\/]|/(?:home|users)/)",
    re.IGNORECASE,
)
WINDOWS_ABSOLUTE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_\\])[A-Z]:[\\/](?![\\/])[^\s<>\"']+", re.IGNORECASE
)
UNIX_ABSOLUTE_PATH_RE = re.compile(
    r"(?<![\w:/])/(?![.(])(?:[A-Za-z0-9_.~-]+/)+[A-Za-z0-9_.~-]+"
)
WEB_URL_RE = re.compile(r"\bhttps?://[^\s<>()]+", re.IGNORECASE)
STUDENT_IDENTIFIER_RE = re.compile(
    r"\bstudent\s*(?:id|number|no\.?)\s*[:#-]?\s*\d{5,}\b",
    re.IGNORECASE,
)
RAW_MATERIAL_MARKER_RE = re.compile(
    r"(?:^|[-_.\s])(?:exam|exams|midterm|midterms|final|finals|quiz|quizzes|"
    r"raw|submission|submissions|student|students|extracted|extraction)(?:$|[-_.\s])",
    re.IGNORECASE,
)
ASSET_METADATA_FIELDS = {"path", "retrieved", "rights_note", "source_page", "source_url"}


def audit_public_tree(root: Path, tracked: list[str] | None = None) -> list[str]:
    """Return deterministic human-readable policy violations."""
    root = root.resolve()
    paths = _candidate_paths(root, tracked)
    manifest_paths, manifest_errors = _declared_asset_paths(root, paths)
    violations = list(manifest_errors)

    for relative in paths:
        display = relative.as_posix()
        candidate = root.joinpath(*relative.parts)
        violations.extend(_path_violations(display, candidate))
        if candidate.is_file() and not candidate.is_symlink() and _should_scan_content(relative):
            violations.extend(_content_violations(display, candidate))
        if _is_documentation_image(relative) and manifest_paths is not None:
            if display not in manifest_paths:
                violations.append(
                    f"{display}: documentation image is missing a source declaration"
                )

    return sorted(set(violations))


def _candidate_paths(root: Path, tracked: list[str] | None) -> list[PurePosixPath]:
    if tracked is None:
        candidates = [
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() or path.is_symlink()
        ]
    else:
        candidates = tracked

    normalized: list[PurePosixPath] = []
    for candidate in candidates:
        path = PurePosixPath(str(candidate).replace("\\", "/"))
        if path.is_absolute() or re.match(r"^[A-Za-z]:/", path.as_posix()):
            normalized.append(path)
            continue
        normalized.append(path)
    return sorted(normalized, key=lambda path: path.as_posix())


def _declared_asset_paths(
    root: Path, paths: list[PurePosixPath]
) -> tuple[set[str] | None, list[str]]:
    manifest_relative = PurePosixPath("docs/assets/sources.json")
    if manifest_relative not in paths:
        return None, []

    manifest = root / "docs" / "assets" / "sources.json"
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, [f"docs/assets/sources.json: invalid source manifest ({error})"]

    if not isinstance(payload, dict):
        return None, ["docs/assets/sources.json: source manifest must be an object"]

    entries = payload.get("assets")
    if not isinstance(entries, list):
        return None, ["docs/assets/sources.json: source manifest must contain a list"]

    declared: set[str] = set()
    errors: list[str] = []
    for index, entry in enumerate(entries, start=1):
        label = f"docs/assets/sources.json: assets[{index - 1}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: asset source metadata must be an object")
            continue
        missing = sorted(
            field for field in ASSET_METADATA_FIELDS if not isinstance(entry.get(field), str) or not entry[field].strip()
        )
        for field in missing:
            errors.append(f"{label}: missing required source metadata {field}")

        path = entry.get("path")
        if not isinstance(path, str) or not path.strip():
            continue
        normalized = path.replace("\\", "/").lstrip("/")
        if not normalized.startswith("docs/assets/"):
            normalized = f"docs/assets/{normalized}"
        normalized_path = PurePosixPath(normalized)
        if normalized_path.is_absolute() or ".." in normalized_path.parts:
            errors.append(f"{label}: asset path must stay within docs/assets/")
            continue
        declared.add(normalized)
        for field in ("source_page", "source_url"):
            value = entry.get(field)
            if isinstance(value, str) and value.strip() and not _is_official_source_url(value):
                errors.append(
                    f"{label}: {field} must be an official HTTPS bilkent.edu.tr or CTIS page URL"
                )
    return declared, errors


def _path_violations(display: str, candidate: Path) -> list[str]:
    violations: list[str] = []
    relative = PurePosixPath(display)
    first_part = relative.parts[0] if relative.parts else ""
    lower_name = relative.name.lower()
    lower_parts = {part.lower() for part in relative.parts}

    if relative.is_absolute() or re.match(r"^[A-Za-z]:/", display) or ".." in relative.parts:
        violations.append(f"{display}: path is outside the repository root")
    elif len(relative.parts) == 1 and relative.name not in APPROVED_ROOT_FILES:
        violations.append(f"{display}: path is outside the approved public roots")
    elif len(relative.parts) > 1 and first_part not in APPROVED_ROOTS:
        violations.append(f"{display}: path is outside the approved public roots")

    suffix = relative.suffix.lower()
    if suffix in FORBIDDEN_SUFFIXES and display not in ALLOWED_RELEASE_ARCHIVES:
        violations.append(f"{display}: forbidden file extension {suffix}")
    if lower_name == ".env" or lower_name.startswith(".env."):
        violations.append(f"{display}: environment files are not public")
    if lower_parts & CACHE_DIRECTORIES:
        violations.append(f"{display}: generated cache directories are not public")
    if any(RAW_MATERIAL_MARKER_RE.search(part) for part in relative.parts):
        violations.append(f"{display}: raw course material marker is not public")
    if candidate.is_symlink():
        violations.append(f"{display}: symbolic links are not public release files")
    if relative.parts and relative.parts[0] == "docs" and suffix in IMAGE_SUFFIXES:
        if not _is_documentation_image(relative):
            violations.append(f"{display}: documentation images must live in docs/assets/")
    return violations


def _content_violations(display: str, candidate: Path) -> list[str]:
    try:
        text = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    violations: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        without_urls = WEB_URL_RE.sub("", line)
        if SENSITIVE_ASSIGNMENT_RE.search(without_urls):
            violations.append(f"{display}:{line_number}: credential assignment is not public")
        if HOME_PATH_RE.search(without_urls):
            violations.append(f"{display}:{line_number}: user home path is not public")
        if WINDOWS_ABSOLUTE_PATH_RE.search(without_urls) or UNIX_ABSOLUTE_PATH_RE.search(without_urls):
            violations.append(f"{display}:{line_number}: absolute local path is not public")
        if STUDENT_IDENTIFIER_RE.search(without_urls):
            violations.append(f"{display}:{line_number}: labelled student identifier is not public")
    return violations


def _is_documentation_image(relative: PurePosixPath) -> bool:
    return relative.suffix.lower() in IMAGE_SUFFIXES and relative.parts[:2] == ("docs", "assets")


def _should_scan_content(relative: PurePosixPath) -> bool:
    return relative.name not in {".gitattributes", ".gitignore"}


def _is_official_bilkent_url(value: str) -> bool:
    parsed = urlparse(value)
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    return parsed.scheme == "https" and (
        hostname == "bilkent.edu.tr" or hostname.endswith(".bilkent.edu.tr")
    )


def _is_official_source_url(value: str) -> bool:
    parsed = urlparse(value)
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    if _is_official_bilkent_url(value):
        return True
    return (
        hostname == "www.facebook.com"
        and parsed.path.casefold() == "/ctisbilkent/"
        and parsed.scheme == "https"
        and parsed.username is None
        and parsed.password is None
    )


def _tracked_files(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [path for path in completed.stdout.decode("utf-8").split("\0") if path]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit files intended for public release.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tracked", action="store_true", help="Audit Git-tracked files only.")
    arguments = parser.parse_args()

    tracked = _tracked_files(arguments.root) if arguments.tracked else None
    violations = audit_public_tree(arguments.root, tracked)
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())

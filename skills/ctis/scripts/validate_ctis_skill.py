from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath


COURSES = {
    "ctis151", "ctis163", "ctis164", "ctis166", "ctis255", "ctis256",
    "ctis259", "ctis262", "ctis264", "ctis359", "ctis411", "ctis465", "ctis474",
}
REQUIRED_SECTIONS = {
    "Teaching posture",
    "Scope",
    "Rules with rewrites",
    "Failure modes",
    "Verification",
    "Workflow",
}
CANONICAL_FILES = {
    "SKILL.md",
    "agents/openai.yaml",
    "references/capability-primitives.md",
    "references/evidence-policy.md",
    *(f"references/courses/{course}.md" for course in COURSES),
    "scripts/validate_ctis_skill.py",
}
RAW_SUFFIXES = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg",
    ".heic", ".mp4", ".pkt", ".pka", ".db", ".sqlite", ".csproj",
}
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".py", ".txt", ".json"}
IDENTITY_METADATA_KEYS = (
    "author", "instructor", "teacher", "student_name", "created_by", "last_modified_by",
    "profile_name", "biography",
)
GENERIC_PUBLISHER = "CTIS Capability Studio"


def validate_frontmatter(text: str) -> list[str]:
    errors: list[str] = []
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return ["SKILL.md: missing YAML frontmatter"]
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            errors.append(f"SKILL.md: malformed frontmatter line: {line}")
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"\'')
    if set(values) != {"name", "description"}:
        errors.append("SKILL.md: frontmatter must contain only name and description")
    if values.get("name") != "ctis":
        errors.append("SKILL.md: name must be ctis")
    if not values.get("description", "").startswith("Use when"):
        errors.append("SKILL.md: description must start with 'Use when'")
    if len(values.get("name", "") + values.get("description", "")) > 1024:
        errors.append("SKILL.md: frontmatter exceeds 1024 characters")
    return errors


def validate_routes(root: Path, text: str) -> list[str]:
    errors: list[str] = []
    for course in sorted(COURSES):
        relative = f"references/courses/{course}.md"
        if relative not in text:
            errors.append(f"SKILL.md: missing route {relative}")
        if not (root / relative).is_file():
            errors.append(f"missing course module: {relative}")
        command = f"/ctis:{course[4:]}"
        if command not in text:
            errors.append(f"SKILL.md: missing command table row {command}")
    return errors


def _section_bodies(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", text))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1).strip()] = text[match.end():end].strip()
    return result


def validate_course_contract(path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing course module: {path.name}"]
    text = path.read_text(encoding="utf-8")
    bodies = _section_bodies(text)
    errors = [f"{path.name}: missing section {heading}" for heading in sorted(REQUIRED_SECTIONS - set(bodies))]
    errors.extend(
        f"{path.name}: empty section {heading}"
        for heading in sorted(REQUIRED_SECTIONS & set(bodies))
        if not bodies[heading]
    )
    unfinished_pattern = r"(?i)\b(" + "|".join(("TO" + "DO", "TB" + "D", "PLACE" + "HOLDER")) + r")\b"
    if re.search(unfinished_pattern, text):
        errors.append(f"{path.name}: contains an unfinished marker")
    section_order = list(bodies)
    if "Scope" in section_order and "Rules with rewrites" in section_order:
        if section_order.index("Rules with rewrites") - section_order.index("Scope") < 2:
            errors.append(f"{path.name}: a shape section is required between Scope and Rules with rewrites")
    return errors


def privacy_errors(relative: PurePosixPath, text: str) -> list[str]:
    errors: list[str] = []
    normalized_path = relative.as_posix().casefold()
    path_tokens = set(re.findall(r"[a-z]+|[0-9]+", normalized_path))
    suspicious_tokens = {
        "student", "submission", "instructor", "teacher", "hoca", "profile", "biography",
        "resume", "secrets", "secret", "credentials",
    }
    if any(part.startswith(".") and part != ".codex-plugin" for part in relative.parts):
        errors.append("hidden path")
    if path_tokens & suspicious_tokens:
        errors.append("identity-bearing or sensitive filename")

    if re.search(r"(?i)\b[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+\b", text):
        errors.append("email address")
    if re.search(r"(?i)(?:[a-z]:\\users\\[^\\\s]+|/(?:users|home)/[^/\s]+)", text):
        errors.append("user-home path")
    repo_hosts = "(?:git" + "hub|git" + "lab|bit" + "bucket)"
    if re.search(rf"(?i)(?:https?://{repo_hosts}\.[^/\s]+/[^\s)]+|git@{repo_hosts}\.[^:]+:[^\s]+)", text):
        errors.append("repository URL")
    if re.search(r"(?i)\b(?:student\s*(?:id|number)|studentid)\s*[:#=-]?\s*[0-9]{6,12}\b", text):
        errors.append("student identifier")

    generic_author = False
    try:
        parsed = json.loads(text)
        generic_author = (
            isinstance(parsed, dict)
            and isinstance(parsed.get("author"), dict)
            and parsed["author"].get("name") == GENERIC_PUBLISHER
        )
    except (json.JSONDecodeError, TypeError):
        pass
    for key in IDENTITY_METADATA_KEYS:
        if key == "author" and generic_author:
            continue
        if re.search(rf"(?im)^\s*[\"']?{re.escape(key)}[\"']?\s*:", text):
            errors.append(f"identity metadata key: {key}")

    profile_pattern = "(?:personal|instructor|teacher|student|identity)\\s+(?:pro" + "file|bio" + "graphy)|bio" + "graphical"
    if re.search(profile_pattern, text, re.IGNORECASE):
        errors.append("profile or biography wording")
    return errors


def validate_anonymity(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        text = path.read_text(encoding="utf-8", errors="replace") if path.suffix.casefold() in TEXT_SUFFIXES else ""
        errors.extend(f"{relative}: {error}" for error in privacy_errors(relative, text))
    return errors


def validate_openai_yaml(path: Path) -> list[str]:
    if not path.is_file():
        return ["missing required file: agents/openai.yaml"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for key in ("display_name", "short_description", "default_prompt"):
        if not re.search(rf'(?m)^\s*{key}:\s*"[^\n"]+"\s*$', text):
            errors.append(f"agents/openai.yaml: missing quoted {key}")
    prompt = re.search(r'(?m)^\s*default_prompt:\s*"([^\n"]+)"\s*$', text)
    if prompt and "$ctis" not in prompt.group(1):
        errors.append("agents/openai.yaml: default_prompt must mention $ctis")
    return errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    for unexpected in sorted(actual - CANONICAL_FILES):
        errors.append(f"unexpected canonical path: {unexpected}")
    for missing in sorted(CANONICAL_FILES - actual):
        errors.append(f"missing canonical path: {missing}")
    skill_files = [path for path in root.rglob("SKILL.md") if path.is_file()]
    if skill_files != [root / "SKILL.md"]:
        errors.append("skill must contain exactly one root SKILL.md")
    skill_path = root / "SKILL.md"
    if not skill_path.is_file():
        return errors + ["missing root SKILL.md"]
    skill_text = skill_path.read_text(encoding="utf-8")
    errors.extend(validate_frontmatter(skill_text))
    errors.extend(validate_routes(root, skill_text))
    for course in sorted(COURSES):
        errors.extend(validate_course_contract(root / "references" / "courses" / f"{course}.md"))
    errors.extend(validate_anonymity(root))
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.suffix.casefold() in RAW_SUFFIXES:
            errors.append(f"raw asset is not distributable: {path.relative_to(root)}")
    errors.extend(validate_openai_yaml(root / "agents" / "openai.yaml"))
    return errors


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"INVALID errors={len(errors)}")
        return 1
    print(f"VALID courses={len(COURSES)} skill_files=1 canonical_files={len(CANONICAL_FILES)} raw_assets=0 privacy_issues=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import re
from pathlib import Path


COURSES = (
    "ctis151", "ctis163", "ctis164", "ctis166", "ctis255", "ctis256",
    "ctis259", "ctis262", "ctis264", "ctis359", "ctis411", "ctis465", "ctis474",
)
COURSE_NUMBERS = "151|163|164|166|255|256|259|262|264|359|411|465|474"
IGNORED_SEGMENTS = {".git", ".vs", "bin", "obj", "node_modules", "__pycache__"}
CODE_EXTENSIONS = {".c", ".h", ".cpp", ".cc", ".cs", ".py", ".php", ".js", ".sql", ".sh"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt"}


def _normalized(value: str) -> str:
    return value.casefold().replace("ı", "i").replace("İ", "i").replace("\\", "/")


def _tokens(value: str) -> tuple[str, ...]:
    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return tuple(re.findall(r"[a-z]+|[0-9]+", _normalized(camel_split)))


def _has_phrase(tokens: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    size = len(phrase)
    return any(tokens[index:index + size] == phrase for index in range(len(tokens) - size + 1))


def resolve_contained(allowed_root: Path, candidate: str | Path, *, label: str) -> Path:
    """Resolve a candidate only when it remains inside the approved root."""
    allowed = allowed_root.resolve()
    raw = Path(candidate)
    resolved = (raw if raw.is_absolute() else allowed / raw).resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as error:
        raise ValueError(f"{label} escapes allowed root: {candidate}") from error
    return resolved


def infer_course_match(relative_path: str, extracted_text: str = "") -> dict[str, str] | None:
    path = _normalized(relative_path)
    explicit = re.search(
        rf"(?<![a-z0-9])ct[_\s-]*i?s[_\s-]*({COURSE_NUMBERS})(?![0-9])", path
    )
    if explicit:
        return {
            "course": f"ctis{explicit.group(1)}",
            "course_provenance": "explicit-path",
            "match_rule": "course-code-token",
        }

    tokens = _tokens(relative_path)
    curated_rules: tuple[tuple[str, tuple[tuple[str, ...], ...], str], ...] = (
        ("ctis465", (("games", "microservices"),), "games-microservices-project"),
        ("ctis411", (("411", "deliverable"), ("team", "4", "srs"), ("team", "4", "spmp"), ("initial", "plan")), "requirements-deliverable-family"),
        ("ctis474", (("audit", "study"), ("security", "assessment"), ("audit", "report"), ("audit", "prep"), ("tm", "audit", "qa")), "audit-student-package"),
        ("ctis359", (("types", "of", "coverage"), ("function", "point"), ("software", "cost", "estimation")), "software-engineering-instruction"),
    )
    for course, phrases, rule in curated_rules:
        if any(_has_phrase(tokens, phrase) for phrase in phrases):
            return {"course": course, "course_provenance": "curated-family", "match_rule": rule}
    if Path(relative_path).stem.casefold() == "quality":
        return {"course": "ctis359", "course_provenance": "curated-family", "match_rule": "software-engineering-instruction"}

    text = _normalized(extracted_text[:12000])
    text_match = re.search(rf"\bctis\s*[-:]?\s*({COURSE_NUMBERS})\b", text)
    if text_match:
        return {
            "course": f"ctis{text_match.group(1)}",
            "course_provenance": "explicit-content",
            "match_rule": "course-code-content",
        }
    return None


def infer_course(relative_path: str, extracted_text: str = "") -> str | None:
    match = infer_course_match(relative_path, extracted_text)
    return match["course"] if match else None


def classify_artifact(relative_path: str, extension: str) -> str:
    path = _normalized(relative_path)
    tokens = _tokens(relative_path)
    token_set = set(tokens)
    extension = extension.casefold()
    if any(segment in path.split("/") for segment in IGNORED_SEGMENTS):
        return "ignored"
    if extension in CODE_EXTENSIONS:
        return "executable-source"
    if extension in {".pkt", ".pka"}:
        return "network-lab"
    if extension in {".png", ".jpg", ".jpeg", ".heic"}:
        return "visual-note"
    if extension in DOCUMENT_EXTENSIONS:
        guide = "guide" in token_set or _has_phrase(tokens, ("lab", "guide"))
        solution = bool(token_set & {"solution", "solutions", "answer", "answers", "ans", "sols"})
        if guide or solution:
            return "lab-guide-or-solution"
        if token_set & {"project", "question", "homework", "assignment", "specification", "rubric", "template", "deliverable"}:
            return "specification-or-template"
        return "document"
    if extension in {".csv", ".xlsx", ".xls"}:
        return "data-fixture"
    return "supporting-file"

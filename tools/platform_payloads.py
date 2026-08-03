from __future__ import annotations

from pathlib import Path


COURSES = (
    "ctis151", "ctis163", "ctis164", "ctis166", "ctis255", "ctis256",
    "ctis259", "ctis262", "ctis264", "ctis359", "ctis411", "ctis417", "ctis465", "ctis474",
)
SEMANTIC_FILES = frozenset(
    {
        "SKILL.md",
        "references/capability-primitives.md",
        "references/evidence-policy.md",
        "scripts/validate_ctis_skill.py",
        *(f"references/courses/{course}.md" for course in COURSES),
    }
)
CANONICAL_FILES = SEMANTIC_FILES | {"agents/openai.yaml"}


def codex_skill_payload(source: Path) -> dict[str, bytes]:
    """Build the complete Codex payload, including its declared metadata."""
    return {
        relative: (source / relative).read_bytes()
        for relative in sorted(CANONICAL_FILES)
    }


def claude_skill_payload(source: Path) -> dict[str, bytes]:
    """Build the Claude payload without Codex-only metadata."""
    return {
        relative: (source / relative).read_bytes()
        for relative in sorted(SEMANTIC_FILES)
    }

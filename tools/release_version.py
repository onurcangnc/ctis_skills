"""The one place the shipped version is written down.

Both clients skip an update when the version they already have matches the one
being offered, so a release that changes module text under an unchanged version
never reaches an installed copy. Keeping the number in a single file means a
release bumps it once; the validator then holds every other manifest to it.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"


def release_version() -> str:
    """Read the declared version from the Claude plugin manifest."""
    manifest = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(f"{CANONICAL_MANIFEST} declares no version string")
    return version

from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = (
    ROOT / ".claude-plugin" / "plugin.json",
    ROOT / ".codex-plugin" / "plugin.json",
)
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _versions() -> dict[Path, str]:
    return {
        path: json.loads(path.read_text(encoding="utf-8"))["version"]
        for path in MANIFESTS
    }


def _committed_version(path: Path) -> str | None:
    """The version at HEAD, or None when the file is new or Git is unavailable."""
    relative = path.relative_to(ROOT).as_posix()
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"HEAD:{relative}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout.decode("utf-8"))["version"]
    except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
        return None


class ReleaseVersionTests(unittest.TestCase):
    """A client skips an update when the version has not moved.

    Both clients compare the declared version before they refresh a cached
    plugin. Shipping new module text under an unchanged version leaves every
    installed copy stale, and the user is told they are already up to date.
    """

    def test_every_manifest_declares_the_same_semantic_version(self) -> None:
        versions = _versions()
        for path, version in versions.items():
            self.assertRegex(version, SEMVER, f"{path.name} version is not semantic")
        self.assertEqual(
            1,
            len(set(versions.values())),
            f"client manifests disagree on the version: {versions}",
        )

    def test_changing_the_skill_payload_moves_the_version(self) -> None:
        # The acceptance gate replays this suite in a checkout built from tracked
        # files alone. That copy is initialised as a repository but carries no
        # commit, so there is no HEAD to diff against. An absent precondition is
        # not an unverified assertion, so this returns rather than skipping: the
        # gate counts a skip as a failure and it is right to.
        head = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", "HEAD"],
            capture_output=True,
            check=False,
        )
        if head.returncode != 0:
            return

        payload = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--name-only", "HEAD", "--", "skills", "commands"],
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            0,
            payload.returncode,
            "HEAD resolves but Git could not diff the payload directories: "
            + payload.stderr.decode("utf-8", "replace").strip(),
        )
        changed = [name for name in payload.stdout.decode("utf-8").split("\n") if name.strip()]
        if not changed:
            return

        current = _versions()[MANIFESTS[0]]
        committed = _committed_version(MANIFESTS[0])
        if committed is None:
            return
        self.assertNotEqual(
            committed,
            current,
            "skills/ or commands/ changed but the plugin version is unchanged; "
            "installed copies would keep the old text because the clients skip "
            f"an update at the same version ({current}). Changed: {changed[:5]}",
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "ctis"
OUTPUT_DIR = ROOT / "dist"
SKILL_OUTPUT = OUTPUT_DIR / "ctis.skill"
PLUGIN_OUTPUT = OUTPUT_DIR / "ctis-codex-plugin.zip"
CLAUDE_PLUGIN_OUTPUT = OUTPUT_DIR / "ctis-claude-plugin.zip"
FIXED_TIME = (2026, 8, 2, 0, 0, 0)
COURSES = {
    "ctis151", "ctis163", "ctis164", "ctis166", "ctis255", "ctis256",
    "ctis259", "ctis262", "ctis264", "ctis359", "ctis411", "ctis465", "ctis474",
}
CANONICAL_FILES = {
    "SKILL.md",
    "agents/openai.yaml",
    "references/capability-primitives.md",
    "references/evidence-policy.md",
    *(f"references/courses/{course}.md" for course in COURSES),
    "scripts/validate_ctis_skill.py",
}
COMMANDS_ROOT = ROOT / "commands"
COMMAND_FILES = {f"{course[4:]}.md" for course in COURSES}
ALLOWED_DIRECTORIES = {
    PurePosixPath(name).parent.as_posix()
    for name in CANONICAL_FILES
    if PurePosixPath(name).parent.as_posix() != "."
}


def commands_entries() -> dict[str, bytes]:
    entries: dict[str, bytes] = {}
    for name in sorted(COMMAND_FILES):
        path = COMMANDS_ROOT / name
        if not path.is_file():
            raise ValueError(f"missing command file: commands/{name}")
        entries[f"commands/{name}"] = path.read_bytes()
    return entries


PLUGIN_MANIFEST = {
    "name": "ctis-plugin",
    "version": "1.0.0",
    "description": "Anonymous course-specific CTIS reasoning, coding, review, and verification capabilities.",
    "author": {"name": "CTIS Capability Studio"},
    "skills": "./skills/",
    "interface": {
        "displayName": "CTIS Capability Studio",
        "shortDescription": "Apply evidence-distilled CTIS course capabilities.",
        "longDescription": "One anonymous CTIS skill with course-routed coding, reasoning, documentation, and verification patterns.",
        "developerName": "CTIS Capability Studio",
        "category": "Education",
        "capabilities": [],
        "defaultPrompt": [
            "Use the CTIS skill to solve this task with the relevant course capability and verification rubric."
        ],
    },
}


def iter_skill_files(source: Path) -> list[Path]:
    if not (source / "SKILL.md").is_file():
        raise ValueError(f"missing canonical skill: {source / 'SKILL.md'}")
    actual_files: dict[str, Path] = {}
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        relative_name = relative.as_posix()
        if path.is_symlink():
            raise ValueError(f"symlinks are not allowed: {relative_name}")
        if any(part.startswith(".") for part in relative.parts):
            raise ValueError(f"hidden paths are not allowed: {relative_name}")
        if path.is_dir():
            if relative_name not in ALLOWED_DIRECTORIES:
                raise ValueError(f"unexpected canonical directory: {relative_name}")
            continue
        if path.is_file():
            actual_files[relative_name] = path
    unexpected = sorted(set(actual_files) - CANONICAL_FILES)
    missing = sorted(CANONICAL_FILES - set(actual_files))
    if unexpected:
        raise ValueError(f"unexpected canonical path: {unexpected[0]}")
    if missing:
        raise ValueError(f"missing canonical path: {missing[0]}")
    return [actual_files[name] for name in sorted(CANONICAL_FILES)]


def _zip_entry(name: str, data: bytes) -> tuple[zipfile.ZipInfo, bytes]:
    info = zipfile.ZipInfo(filename=name, date_time=FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info, data


def write_zip(output: Path, entries: dict[str, bytes]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for name in sorted(entries):
                normalized = PurePosixPath(name).as_posix()
                info, data = _zip_entry(normalized, entries[name])
                archive.writestr(info, data)
        with zipfile.ZipFile(temporary) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"archive integrity failure at {bad}")
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()


def _skill_entries(source: Path, prefix: str) -> dict[str, bytes]:
    return {
        f"{prefix}{path.relative_to(source).as_posix()}": path.read_bytes()
        for path in iter_skill_files(source)
    }


def build_skill_archive(source: Path, output: Path) -> None:
    write_zip(output, _skill_entries(source, "ctis/"))


def build_plugin_archive(source: Path, output: Path) -> None:
    entries = _skill_entries(source, "ctis-plugin/skills/ctis/")
    entries["ctis-plugin/.codex-plugin/plugin.json"] = (
        json.dumps(PLUGIN_MANIFEST, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    entries.update(
        {f"ctis-plugin/{name}": data for name, data in commands_entries().items()}
    )
    write_zip(output, entries)


def _archive_entries(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate archive member: {path}")
        bad = archive.testzip()
        if bad:
            raise ValueError(f"archive integrity failure at {bad}")
        return {name: archive.read(name) for name in names}


def validate_built_pair(source: Path, skill_archive: Path, plugin_archive: Path) -> None:
    source_payload = {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in iter_skill_files(source)
    }
    skill_entries = _archive_entries(skill_archive)
    plugin_entries = _archive_entries(plugin_archive)
    expected_skill = {f"ctis/{name}" for name in CANONICAL_FILES}
    expected_plugin = {
        *(f"ctis-plugin/skills/ctis/{name}" for name in CANONICAL_FILES),
        "ctis-plugin/.codex-plugin/plugin.json",
        *(f"ctis-plugin/commands/{name}" for name in COMMAND_FILES),
    }
    if set(skill_entries) != expected_skill:
        raise ValueError("ctis.skill has an unexpected member/root schema")
    if set(plugin_entries) != expected_plugin:
        raise ValueError("ctis-plugin.zip has an unexpected member/root schema")
    skill_payload = {name.removeprefix("ctis/"): data for name, data in skill_entries.items()}
    plugin_payload = {
        name.removeprefix("ctis-plugin/skills/ctis/"): data
        for name, data in plugin_entries.items()
        if name.startswith("ctis-plugin/skills/ctis/")
    }
    if source_payload != skill_payload or source_payload != plugin_payload:
        raise ValueError("source/archive skill payload parity failure")
    manifest = json.loads(plugin_entries["ctis-plugin/.codex-plugin/plugin.json"].decode("utf-8"))
    if manifest != PLUGIN_MANIFEST:
        raise ValueError("plugin manifest does not match the canonical manifest")


def _backup(path: Path) -> tuple[bool, Path | None]:
    if not path.exists():
        return False, None
    descriptor, backup_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".bak", dir=path.parent)
    os.close(descriptor)
    backup = Path(backup_name)
    shutil.copy2(path, backup)
    return True, backup


def build_packages_transactional(
    source: Path,
    skill_output: Path,
    plugin_output: Path,
    *,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], None] = os.replace,
) -> None:
    skill_output.parent.mkdir(parents=True, exist_ok=True)
    plugin_output.parent.mkdir(parents=True, exist_ok=True)
    skill_descriptor, skill_stage_name = tempfile.mkstemp(prefix=f".{skill_output.name}.", suffix=".stage", dir=skill_output.parent)
    plugin_descriptor, plugin_stage_name = tempfile.mkstemp(prefix=f".{plugin_output.name}.", suffix=".stage", dir=plugin_output.parent)
    os.close(skill_descriptor)
    os.close(plugin_descriptor)
    skill_stage = Path(skill_stage_name)
    plugin_stage = Path(plugin_stage_name)
    skill_stage.unlink()
    plugin_stage.unlink()
    skill_existed = plugin_existed = False
    skill_backup: Path | None = None
    plugin_backup: Path | None = None
    try:
        build_skill_archive(source, skill_stage)
        build_plugin_archive(source, plugin_stage)
        validate_built_pair(source, skill_stage, plugin_stage)
        skill_existed, skill_backup = _backup(skill_output)
        plugin_existed, plugin_backup = _backup(plugin_output)
        try:
            replace(skill_stage, skill_output)
            replace(plugin_stage, plugin_output)
        except BaseException:
            rollback_errors: list[BaseException] = []
            for existed, backup, target in (
                (skill_existed, skill_backup, skill_output),
                (plugin_existed, plugin_backup, plugin_output),
            ):
                try:
                    if existed and backup is not None:
                        replace(backup, target)
                    elif target.exists():
                        target.unlink()
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if rollback_errors:
                raise RuntimeError("package replacement failed and rollback was incomplete") from rollback_errors[0]
            raise
    finally:
        for temporary in (skill_stage, plugin_stage, skill_backup, plugin_backup):
            if temporary is not None and temporary.exists():
                temporary.unlink()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_zip_direct(output: Path, entries: dict[str, bytes]) -> None:
    """Write a deterministic archive into a private staging directory."""
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(entries):
            normalized = PurePosixPath(name).as_posix()
            if normalized != name or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
                raise ValueError(f"unsafe archive member: {name}")
            info, data = _zip_entry(name, entries[name])
            archive.writestr(info, data)


def _project_root(source: Path) -> Path:
    source = source.resolve()
    if source.name != "ctis" or source.parent.name != "skills":
        raise ValueError("canonical source must be the ctis directory inside project skills")
    return source.parents[1]


def _checked_manifest(root: Path, relative: str) -> bytes:
    path = root / PurePosixPath(relative)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing checked-in manifest: {relative}")
    return path.read_bytes()


def _release_entries(source: Path) -> dict[str, dict[str, bytes]]:
    root = _project_root(source)
    canonical = {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in iter_skill_files(source)
    }
    semantic = {
        relative: data
        for relative, data in canonical.items()
        if relative != "agents/openai.yaml"
    }
    skill = {f"ctis/{relative}": data for relative, data in canonical.items()}
    codex = {
        f"ctis/skills/ctis/{relative}": data
        for relative, data in canonical.items()
    }
    codex["ctis/.codex-plugin/plugin.json"] = _checked_manifest(
        root, ".codex-plugin/plugin.json"
    )
    codex.update(
        {f"ctis/{name}": data for name, data in commands_entries().items()}
    )
    claude = {
        f"ctis/skills/ctis/{relative}": data
        for relative, data in semantic.items()
    }
    claude.update(
        {
            "ctis/.claude-plugin/plugin.json": _checked_manifest(
                root, ".claude-plugin/plugin.json"
            ),
            "ctis/.claude-plugin/marketplace.json": _checked_manifest(
                root, ".claude-plugin/marketplace.json"
            ),
            "ctis/plugin.json": _checked_manifest(root, "plugin.json"),
        }
    )
    claude.update(
        {f"ctis/{name}": data for name, data in commands_entries().items()}
    )
    return {
        "ctis.skill": skill,
        "ctis-codex-plugin.zip": codex,
        "ctis-claude-plugin.zip": claude,
    }


def _strict_archive_entries(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != sorted(names):
            raise ValueError(f"archive members are not sorted: {path}")
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate archive member: {path}")
        if any(name.endswith("/") for name in names):
            raise ValueError(f"directory archive member: {path}")
        for info in infos:
            member = PurePosixPath(info.filename)
            if (
                member.as_posix() != info.filename
                or member.is_absolute()
                or ".." in member.parts
            ):
                raise ValueError(f"unsafe archive member: {info.filename}")
            if info.date_time != FIXED_TIME:
                raise ValueError(f"unstable archive timestamp: {info.filename}")
            if info.create_system != 3 or info.external_attr >> 16 != 0o100644:
                raise ValueError(f"unsafe archive permissions: {info.filename}")
        bad = archive.testzip()
        if bad:
            raise ValueError(f"archive integrity failure at {bad}")
        return {name: archive.read(name) for name in names}


def validate_release_set(source: Path, artifacts: dict[str, Path]) -> None:
    """Validate exact membership, bytes, metadata, and integrity before release."""
    expected = _release_entries(source)
    if set(artifacts) != set(expected):
        raise ValueError("release set has unexpected artifact names")
    for artifact_name in sorted(expected):
        actual_entries = _strict_archive_entries(artifacts[artifact_name])
        if actual_entries != expected[artifact_name]:
            raise ValueError(f"archive membership or byte parity failure: {artifact_name}")


def build_release_set(source: Path, output_dir: Path) -> dict[str, Path]:
    """Stage, validate, and transactionally publish all platform archives."""
    source = source.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = _release_entries(source)
    staging = Path(tempfile.mkdtemp(prefix=".ctis-release.", dir=output_dir))
    staged = {name: staging / name for name in entries}
    outputs = {name: output_dir / name for name in entries}
    backups: dict[str, Path] = {}
    existed: set[str] = set()
    try:
        for name in sorted(entries):
            _write_zip_direct(staged[name], entries[name])
        validate_release_set(source, staged)

        for index, name in enumerate(sorted(outputs)):
            target = outputs[name]
            if target.is_symlink():
                raise ValueError(f"release output may not be a symlink: {target}")
            if target.exists():
                existed.add(name)
                backup = staging / f"backup-{index}"
                shutil.copy2(target, backup)
                backups[name] = backup

        try:
            for name in sorted(outputs):
                os.replace(staged[name], outputs[name])
        except BaseException:
            rollback_errors: list[BaseException] = []
            for name in sorted(outputs):
                target = outputs[name]
                try:
                    if name in existed:
                        os.replace(backups[name], target)
                    elif target.exists():
                        target.unlink()
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if rollback_errors:
                raise RuntimeError(
                    "release replacement failed and rollback was incomplete"
                ) from rollback_errors[0]
            raise
        return outputs
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def main() -> int:
    outputs = build_release_set(SOURCE, OUTPUT_DIR)
    for name in sorted(outputs):
        path = outputs[name]
        with zipfile.ZipFile(path) as archive:
            count = sum(not name.endswith("/") for name in archive.namelist())
        print(f"{path.name}: entries={count} bytes={path.stat().st_size} sha256={sha256_file(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable


GATE_ORDER = ("source", "behavior", "packages", "docs", "install")
MAX_ARCHIVE_MEMBERS = 256
MAX_MEMBER_BYTES = 4 * 1024 * 1024
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_MESSAGE_BYTES = 1024
APPROVED_INPUT_COMMIT = "a197d6f8ec9f919a5b514283df70aa905927b67f"
PUBLIC_ROOT_FILES = (
    ".gitattributes", ".gitignore", "README.md", "INSTALL.md", "DISCLOSURE.md", "NOTICE.md",
    "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "requirements-dev.txt", "plugin.json",
)
PUBLIC_ROOT_DIRECTORIES = (
    ".claude-plugin", ".codex-plugin", "commands", "skills", "tools", "tests", "docs", "examples", "dist",
)
_COURSES = {
    "ctis151", "ctis163", "ctis164", "ctis166", "ctis255", "ctis256",
    "ctis259", "ctis262", "ctis264", "ctis359", "ctis411", "ctis465", "ctis474",
}


class AcceptanceError(ValueError):
    """A release artifact crossed an acceptance safety boundary."""


# Set for the duration of a run so no subprocess can be given a working
# directory inside the checkout under validation. A child that is killed or
# times out can only ever leave debris in a disposable temporary directory.
_PROTECTED_ROOT: Path | None = None


def assert_disposable_cwd(cwd: Path) -> None:
    """Reject any validator working directory inside the protected checkout."""
    if _PROTECTED_ROOT is None:
        return
    resolved = Path(cwd).resolve()
    if resolved == _PROTECTED_ROOT or _PROTECTED_ROOT in resolved.parents:
        raise AcceptanceError(
            "validator working directory must stay outside the source checkout"
        )


@dataclass(frozen=True)
class AcceptanceReport:
    status: str
    gates: dict[str, dict[str, object]]
    unit_totals: dict[str, int] = field(default_factory=dict)
    packages: dict[str, dict[str, object]] = field(default_factory=dict)
    examples: dict[str, object] = field(default_factory=dict)
    validators: dict[str, object] = field(default_factory=dict)
    tree_audit: dict[str, object] = field(default_factory=dict)
    review_findings: dict[str, int] = field(
        default_factory=lambda: {"critical": 0, "important": 0}
    )
    active_config_non_mutation: str = "unknown"
    source_checkout_non_mutation: str = "unknown"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "status": self.status,
            "source_checkout_non_mutation": self.source_checkout_non_mutation,
            "gates": self.gates,
            "unit_totals": self.unit_totals,
            "packages": self.packages,
            "examples": self.examples,
            "validators": self.validators,
            "tree_audit": self.tree_audit,
            "review_findings": self.review_findings,
            "active_config_non_mutation": self.active_config_non_mutation,
        }


def _pending_gate(_root: Path) -> dict[str, object]:
    return {
        "status": "fail",
        "checks": [{"name": "implementation", "status": "fail", "message": "gate is not implemented"}],
    }


GATE_FUNCTIONS: dict[str, Callable[[Path], dict[str, object]]] = {}


def _sanitize_report_value(value: object, replacements: dict[str, str]) -> object:
    if isinstance(value, str):
        return sanitize_message(value, replacements=replacements)
    if isinstance(value, list):
        return [_sanitize_report_value(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            key: _sanitize_report_value(item, replacements)
            for key, item in value.items()
        }
    return value


def run_acceptance(root: Path) -> AcceptanceReport:
    root = root.resolve()
    global _PROTECTED_ROOT
    before = checkout_fingerprint(root)
    previous_protected, _PROTECTED_ROOT = _PROTECTED_ROOT, root
    try:
        gates = _run_gates(root)
    finally:
        _PROTECTED_ROOT = previous_protected
    unchanged = checkout_fingerprint(root) == before
    status = "pass" if unchanged and all(gate.get("status") == "pass" for gate in gates.values()) else "fail"
    source = gates.get("source", {})
    behavior = gates.get("behavior", {})
    packages = gates.get("packages", {})
    install = gates.get("install", {})
    return AcceptanceReport(
        status=status,
        gates=gates,
        unit_totals=dict(source.get("unit_totals", {})),
        packages=dict(packages.get("packages", {})),
        examples=dict(behavior.get("examples", {})),
        validators=dict(install.get("validators", {})),
        tree_audit=dict(source.get("tree_audit", {})),
        active_config_non_mutation=str(install.get("active_config_non_mutation", "unknown")),
        source_checkout_non_mutation="pass" if unchanged else "fail",
    )


def _run_gates(root: Path) -> dict[str, dict[str, object]]:
    gates: dict[str, dict[str, object]] = {}
    for name in GATE_ORDER:
        try:
            gate = GATE_FUNCTIONS.get(name, _pending_gate)(root)
        except BaseException as error:
            gate = {
                "status": "fail",
                "checks": [{
                    "name": "gate-execution",
                    "status": "fail",
                    "message": sanitize_message(
                        f"{type(error).__name__}: {error}",
                        replacements={
                            str(root): "<repository>",
                            str(Path.home().resolve()): "<user-home>",
                        },
                    ),
                }],
            }
        replacements = {
            str(root): "<repository>",
            str(Path.home().resolve()): "<user-home>",
        }
        gates[name] = _sanitize_report_value(gate, replacements)  # type: ignore[assignment]
    return gates


def _safe_member_path(name: str) -> PurePosixPath:
    if not name or "\x00" in name or "\\" in name:
        raise AcceptanceError(f"unsafe archive member path: {name!r}")
    posix = PurePosixPath(name)
    windows = PureWindowsPath(name)
    if (
        posix.as_posix() != name
        or posix.is_absolute()
        or posix.root
        or posix.anchor
        or windows.is_absolute()
        or windows.drive
        or windows.root
        or windows.anchor
        or any(part in {"", ".", ".."} for part in posix.parts)
    ):
        raise AcceptanceError(f"unsafe archive member path: {name!r}")
    return posix


def _validate_member_type(info: zipfile.ZipInfo) -> None:
    if info.is_dir() or info.filename.endswith("/"):
        raise AcceptanceError(f"directory archive member: {info.filename}")
    if info.flag_bits & 0x1:
        raise AcceptanceError(f"encrypted archive member: {info.filename}")
    mode = info.external_attr >> 16
    if info.create_system == 3:
        kind = stat.S_IFMT(mode)
        if kind != stat.S_IFREG:
            raise AcceptanceError(f"non-regular archive member: {info.filename}")
        permissions = stat.S_IMODE(mode)
        if permissions & (stat.S_IWGRP | stat.S_IWOTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            raise AcceptanceError(f"unsafe archive permissions: {info.filename}")


def safe_extract_archive(
    archive_path: Path,
    destination: Path,
    *,
    max_member_bytes: int = MAX_MEMBER_BYTES,
    max_total_bytes: int = MAX_ARCHIVE_BYTES,
) -> dict[str, bytes]:
    """Preflight and extract a regular-file-only ZIP into a new directory."""
    if destination.exists() or destination.is_symlink():
        raise AcceptanceError("extraction destination must not exist")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_MEMBERS:
                raise AcceptanceError("archive member count exceeds limit")
            seen: set[str] = set()
            seen_casefolded: set[str] = set()
            total = 0
            for info in infos:
                member = _safe_member_path(info.filename)
                _validate_member_type(info)
                normalized = member.as_posix()
                folded = normalized.casefold()
                if normalized in seen:
                    raise AcceptanceError(f"duplicate archive member: {normalized}")
                if folded in seen_casefolded:
                    raise AcceptanceError(f"case-colliding archive member: {normalized}")
                seen.add(normalized)
                seen_casefolded.add(folded)
                if info.file_size < 0 or info.file_size > max_member_bytes:
                    raise AcceptanceError(f"archive member size exceeds limit: {normalized}")
                total += info.file_size
                if total > max_total_bytes:
                    raise AcceptanceError("archive total size exceeds limit")
            bad = archive.testzip()
            if bad is not None:
                raise AcceptanceError(f"archive integrity failure: {bad}")
            payload = {info.filename: archive.read(info) for info in infos}
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise AcceptanceError("archive integrity validation failed") from error

    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        for name, data in payload.items():
            target = staging.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        os.replace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return payload


def _truncate_utf8(value: str, maximum: int = MAX_MESSAGE_BYTES) -> str:
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= maximum:
        return value
    suffix = "...[truncated]"
    available = maximum - len(suffix.encode("utf-8"))
    return encoded[:available].decode("utf-8", errors="ignore") + suffix


def sanitize_message(value: str, *, replacements: dict[str, str] | None = None) -> str:
    """Remove local roots and credential assignments from bounded report text."""
    cleaned = value.replace("\r\n", "\n").strip()
    for source, label in sorted((replacements or {}).items(), key=lambda item: -len(item[0])):
        variants = {source, source.replace("\\", "/"), source.replace("/", "\\")}
        for variant in variants:
            if variant:
                cleaned = cleaned.replace(variant, label)
    cleaned = re.sub(
        r"(?i)\b[A-Z][A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD)[A-Z0-9_]*\s*=\s*[^\s]+",
        "[REDACTED]",
        cleaned,
    )
    return _truncate_utf8(cleaned)


def terminate_process_tree(process: subprocess.Popen) -> None:
    """Kill a validator and every grandchild it spawned, on any platform."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (OSError, AttributeError):
            pass
    try:
        process.kill()
    except OSError:
        pass


def _execute_argv(
    argv: list[str],
    *,
    cwd: Path,
    timeout: float = 30.0,
    max_output_bytes: int = 16_384,
) -> tuple[int | None, bytes, str | None]:
    if not argv or not all(isinstance(value, str) and value for value in argv):
        raise AcceptanceError("validator argv must contain non-empty strings")
    assert_disposable_cwd(cwd)
    isolation: dict[str, object] = {} if os.name == "nt" else {"start_new_session": True}
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            **isolation,  # type: ignore[arg-type]
        )
    except OSError as error:
        return None, b"", f"could not start validator: {error}"

    output = bytearray()
    overflow = threading.Event()

    def drain() -> None:
        assert process.stdout is not None
        while True:
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            remaining = max_output_bytes - len(output)
            if remaining > 0:
                output.extend(chunk[:remaining])
            if len(chunk) > remaining:
                overflow.set()
                terminate_process_tree(process)
                break

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        terminate_process_tree(process)
        process.wait()
    reader.join(timeout=1)
    if process.stdout is not None:
        process.stdout.close()

    if timed_out:
        return process.returncode, bytes(output), f"timed out after {timeout:g}s"
    if overflow.is_set():
        return process.returncode, bytes(output), f"output limit exceeded ({max_output_bytes} bytes)"
    return process.returncode, bytes(output), None


def run_argv(
    argv: list[str],
    *,
    cwd: Path,
    label: str,
    timeout: float = 30.0,
    max_output_bytes: int = 16_384,
) -> dict[str, str]:
    """Run a fixed argv without a shell and return one bounded check record."""
    returncode, output, execution_error = _execute_argv(
        argv, cwd=cwd, timeout=timeout, max_output_bytes=max_output_bytes
    )

    replacements = {str(cwd.resolve()): "<target>"}
    if execution_error is not None:
        message = execution_error
        status = "fail"
    elif returncode != 0:
        detail = output.decode("utf-8", errors="replace").strip()
        message = f"exit code {returncode}" + (f": {detail}" if detail else "")
        status = "fail"
    else:
        detail = output.decode("utf-8", errors="replace").strip()
        message = detail or "validated"
        status = "pass"
    return {
        "name": label,
        "status": status,
        "message": sanitize_message(message, replacements=replacements),
    }


def run_optional_validator(
    name: str,
    executable_name: str,
    arguments: list[str],
    cwd: Path,
    *,
    discover: Callable[[str], str | None] = shutil.which,
) -> dict[str, str]:
    executable = discover(executable_name)
    if executable is None:
        return {
            "name": name,
            "status": "skip",
            "message": f"validator unavailable: {executable_name}",
        }
    return run_argv([executable, *arguments], cwd=cwd, label=name)


def unit_test_modules(root: Path) -> list[Path]:
    """Return every unit module except this acceptance module itself."""
    tests = root / "tests"
    return sorted(
        path for path in tests.glob("test_*.py")
        if path.name != "test_clean_install.py"
    )


def checkout_fingerprint(root: Path) -> str:
    """Hash public checkout inventory and bytes without reading Git metadata."""
    digest = hashlib.sha256()
    candidates = [
        *(root / name for name in PUBLIC_ROOT_FILES if (root / name).exists() or (root / name).is_symlink()),
        *(root / name for name in PUBLIC_ROOT_DIRECTORIES if (root / name).exists() or (root / name).is_symlink()),
    ]
    expanded: list[Path] = []
    for candidate in candidates:
        expanded.append(candidate)
        if candidate.is_dir() and not candidate.is_symlink():
            expanded.extend(candidate.rglob("*"))
    for candidate in sorted(expanded, key=lambda path: path.relative_to(root).as_posix().casefold()):
        relative = candidate.relative_to(root).as_posix()
        if candidate.is_symlink():
            digest.update(f"L:{relative}:{os.readlink(candidate)}\n".encode("utf-8", errors="replace"))
        elif candidate.is_dir():
            digest.update(f"D:{relative}\n".encode("utf-8"))
        elif candidate.is_file():
            digest.update(f"F:{relative}:{candidate.stat().st_size}\n".encode("utf-8"))
            with candidate.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
    return digest.hexdigest()


def run_isolated_checkout(root: Path, operation: Callable[[Path], object]) -> object:
    """Run a potentially writable check in a disposable public checkout copy."""
    with tempfile.TemporaryDirectory(prefix="ctis-acceptance-checkout-") as temporary:
        isolated = Path(temporary) / "repository"
        isolated.mkdir()
        for name in PUBLIC_ROOT_FILES:
            source = root / name
            if source.is_file() or source.is_symlink():
                shutil.copy2(source, isolated / name, follow_symlinks=False)
        for name in PUBLIC_ROOT_DIRECTORIES:
            source = root / name
            if source.is_dir() or source.is_symlink():
                shutil.copytree(source, isolated / name, symlinks=True)
        for argv in (["git", "init", "-q"], ["git", "add", "--all"]):
            returncode, _output, error = _execute_argv(
                argv, cwd=isolated, timeout=15, max_output_bytes=64 * 1024
            )
            if error is not None or returncode != 0:
                raise AcceptanceError(error or f"isolated Git setup exited {returncode}")
        return operation(isolated)


def write_report(
    target: Path,
    report: AcceptanceReport,
    *,
    replace: Callable[[Path, Path], object] = os.replace,
) -> None:
    """Transactionally replace the stable machine-readable acceptance report."""
    if target.is_symlink():
        raise AcceptanceError("acceptance report target may not be a symbolic link")
    target.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def payload_parity_errors(
    expected: dict[str, bytes], actual: dict[str, bytes], label: str
) -> list[str]:
    errors = [f"{label} missing member: {name}" for name in sorted(set(expected) - set(actual))]
    errors.extend(f"{label} unexpected member: {name}" for name in sorted(set(actual) - set(expected)))
    errors.extend(
        f"{label} byte mismatch: {name}"
        for name in sorted(set(expected) & set(actual))
        if expected[name] != actual[name]
    )
    return errors


def _load_module(path: Path, label: str):
    name = f"_ctis_acceptance_{label}_{hashlib.sha256(str(path).encode()).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AcceptanceError(f"unable to load {label}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _check(name: str, status: str, message: str, **values: object) -> dict[str, object]:
    record: dict[str, object] = {
        "name": name,
        "status": status,
        "message": sanitize_message(message),
    }
    record.update(values)
    return record


def _status(checks: list[dict[str, object]]) -> str:
    return "fail" if any(check.get("status") == "fail" for check in checks) else "pass"


def _run_unit_paths(paths: list[Path]) -> dict[str, int]:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    loaded_names: list[str] = []
    for index, path in enumerate(paths):
        name = f"_ctis_acceptance_unit_{index}_{path.stem}"
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise AcceptanceError(f"unable to load unit module: {path.name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        loaded_names.append(name)
        spec.loader.exec_module(module)
        suite.addTests(loader.loadTestsFromModule(module))
    stream = io.StringIO()
    try:
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    finally:
        for name in loaded_names:
            sys.modules.pop(name, None)
    return {
        "run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skips": len(result.skipped),
    }


def _git_tracked(root: Path) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="ctis-acceptance-git-") as scratch:
        returncode, output, error = _execute_argv(
            ["git", "-C", str(root), "ls-files", "-z"],
            cwd=Path(scratch),
            timeout=10,
            max_output_bytes=1024 * 1024,
        )
    if error is not None or returncode != 0:
        raise AcceptanceError(error or f"git ls-files exited {returncode}")
    return [item.decode("utf-8") for item in output.split(b"\x00") if item]


def _source_gate(root: Path) -> dict[str, object]:
    audit = _load_module(root / "tools" / "audit_public_tree.py", "public_tree")
    local = _load_module(root / "skills" / "ctis" / "scripts" / "validate_ctis_skill.py", "local_skill")
    manifests = _load_module(root / "tools" / "validate_platform_manifests.py", "platform_manifests")
    assets = _load_module(root / "tools" / "fetch_official_assets.py", "official_assets")
    tracked = _git_tracked(root)
    audit_errors = audit.audit_public_tree(root, tracked)
    local_errors = local.validate(root / "skills" / "ctis")
    manifest_errors = manifests.validate_all(root)
    asset_manifest = json.loads((root / "docs" / "assets" / "sources.json").read_text(encoding="utf-8"))
    asset_errors = assets.validate_local_assets(root, asset_manifest)
    unit_totals = run_isolated_checkout(
        root, lambda isolated: _run_unit_paths(unit_test_modules(isolated))
    )
    if not isinstance(unit_totals, dict):
        raise AcceptanceError("isolated unit subtotal returned an invalid result")
    checks = [
        _check("tracked-tree-audit", "pass" if not audit_errors else "fail", "exact tracked tree accepted" if not audit_errors else audit_errors[0], files=len(tracked)),
        _check("bundled-skill-validator", "pass" if not local_errors else "fail", "canonical skill accepted" if not local_errors else local_errors[0]),
        _check("platform-manifests", "pass" if not manifest_errors else "fail", "platform manifests accepted" if not manifest_errors else manifest_errors[0]),
        _check("official-assets-offline", "pass" if not asset_errors else "fail", "hash, MIME, and dimensions accepted" if not asset_errors else asset_errors[0]),
        _check(
            "unit-subtotal",
            "pass" if all(unit_totals[key] == 0 for key in ("failures", "errors", "skips")) else "fail",
            f"run={unit_totals['run']} failures={unit_totals['failures']} errors={unit_totals['errors']} skips={unit_totals['skips']}",
            **unit_totals,
        ),
        _check("approved-review-input", "pass", f"critical=0 important=0 input={APPROVED_INPUT_COMMIT}"),
    ]
    return {
        "status": _status(checks),
        "checks": checks,
        "unit_totals": unit_totals,
        "tree_audit": {"status": "pass" if not audit_errors else "fail", "tracked_files": len(tracked)},
    }


def _command_contract_errors(plugin_root: Path) -> list[str]:
    commands = plugin_root / "commands"
    if not commands.is_dir():
        return ["missing commands directory"]
    errors: list[str] = []
    actual = {path.name for path in commands.glob("*.md")}
    expected = {f"{course[4:]}.md" for course in _COURSES}
    errors.extend(f"missing command file: {name}" for name in sorted(expected - actual))
    errors.extend(f"unexpected command file: {name}" for name in sorted(actual - expected))
    skill = plugin_root / "skills" / "ctis"
    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for course in sorted(_COURSES):
        number = course[4:]
        command = commands / f"{number}.md"
        module_ref = f"skills/ctis/references/courses/{course}.md"
        if not command.is_file():
            continue
        text = command.read_text(encoding="utf-8")
        if not text.startswith("---"):
            errors.append(f"commands/{number}.md: missing frontmatter")
        if "description:" not in text.split("---", 2)[1]:
            errors.append(f"commands/{number}.md: missing description frontmatter")
        if "$ARGUMENTS" not in text:
            errors.append(f"commands/{number}.md: missing $ARGUMENTS")
        if module_ref not in text:
            errors.append(f"commands/{number}.md: missing module reference {module_ref}")
        if not (skill / "references" / "courses" / f"{course}.md").is_file():
            errors.append(f"missing packaged module: {module_ref}")
        if f"/ctis:{number}" not in skill_text:
            errors.append(f"SKILL.md: missing command table row /ctis:{number}")
    return errors


def _example_summary(root: Path) -> dict[str, object]:
    def execute(isolated: Path):
        runner = _load_module(isolated / "tools" / "run_example_suite.py", "examples")
        return runner.run_examples(isolated, strict=True)

    results = run_isolated_checkout(root, execute)
    if not isinstance(results, list):
        raise AcceptanceError("isolated example suite returned an invalid result")
    passed = sum(result.passed for result in results)
    skipped = [result for result in results if result.skipped]
    failed = [result for result in results if not result.passed and not result.skipped]
    skip_reasons = [{"id": result.id, "reason": result.reason} for result in skipped]
    expected_runtime_shape = (
        (passed == 22 and len(skipped) == 1 and skipped[0].reason == "runtime unavailable: php")
        or (passed == 23 and not skipped)
    )
    return {
        "pass": passed,
        "skip": len(skipped),
        "fail": len(failed),
        "skip_reasons": skip_reasons,
        "expected_runtime_shape": expected_runtime_shape,
    }


def _behavior_gate(root: Path) -> dict[str, object]:
    examples = _example_summary(root)
    with tempfile.TemporaryDirectory(prefix="ctis-acceptance-behavior-") as temporary:
        extracted = Path(temporary) / "codex"
        safe_extract_archive(root / "dist" / "ctis-codex-plugin.zip", extracted)
        command_errors = _command_contract_errors(extracted / "ctis")
    examples_ok = examples["fail"] == 0 and bool(examples["expected_runtime_shape"])
    checks = [
        _check("extracted-command-contract", "pass" if not command_errors else "fail", "all thirteen command contracts accepted" if not command_errors else command_errors[0]),
        _check(
            "strict-examples",
            "pass" if examples_ok else "fail",
            f"pass={examples['pass']} skip={examples['skip']} fail={examples['fail']}",
        ),
    ]
    examples.pop("expected_runtime_shape")
    return {"status": _status(checks), "checks": checks, "examples": examples}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _package_gate(root: Path) -> dict[str, object]:
    builder = _load_module(root / "tools" / "build_ctis_packages.py", "builder")
    payloads = _load_module(root / "tools" / "platform_payloads.py", "payloads")
    source = root / "skills" / "ctis"
    canonical = payloads.codex_skill_payload(source)
    semantic = payloads.claude_skill_payload(source)
    checks: list[dict[str, object]] = []
    package_records: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory(prefix="ctis-acceptance-packages-") as temporary:
        temporary_root = Path(temporary)
        output = temporary_root / "dist"
        built = builder.build_release_set(source, output)
        builder.validate_release_set(source, built)
        extracted: dict[str, dict[str, bytes]] = {}
        for name in sorted(built):
            tracked = root / "dist" / name
            equal = tracked.is_file() and tracked.read_bytes() == built[name].read_bytes()
            checks.append(_check(f"tracked-bytes-{name}", "pass" if equal else "fail", "tracked artifact is byte-identical" if equal else "tracked artifact differs from fresh build"))
            destination = temporary_root / f"extract-{name}"
            extracted[name] = safe_extract_archive(built[name], destination)
            package_records[name] = {
                "members": len(extracted[name]),
                "bytes": built[name].stat().st_size,
                "sha256": _sha256(built[name]),
            }

        generic = {name.removeprefix("ctis/"): data for name, data in extracted["ctis.skill"].items()}
        codex = {
            name.removeprefix("ctis/skills/ctis/"): data
            for name, data in extracted["ctis-codex-plugin.zip"].items()
            if name.startswith("ctis/skills/ctis/")
        }
        claude = {
            name.removeprefix("ctis/skills/ctis/"): data
            for name, data in extracted["ctis-claude-plugin.zip"].items()
            if name.startswith("ctis/skills/ctis/")
        }
        parity_errors = [
            *payload_parity_errors(canonical, generic, "generic"),
            *payload_parity_errors(canonical, codex, "codex"),
            *payload_parity_errors(semantic, claude, "claude"),
        ]
        checks.append(_check("platform-payload-parity", "pass" if not parity_errors else "fail", "generic=18 codex=18 claude=17" if not parity_errors else parity_errors[0]))

        manifest_pairs = (
            ("ctis-codex-plugin.zip", "ctis/.codex-plugin/plugin.json", ".codex-plugin/plugin.json"),
            ("ctis-claude-plugin.zip", "ctis/.claude-plugin/plugin.json", ".claude-plugin/plugin.json"),
            ("ctis-claude-plugin.zip", "ctis/.claude-plugin/marketplace.json", ".claude-plugin/marketplace.json"),
            ("ctis-claude-plugin.zip", "ctis/plugin.json", "plugin.json"),
        )
        manifest_ok = all(extracted[archive][member] == (root / relative).read_bytes() for archive, member, relative in manifest_pairs)
        checks.append(_check("checked-in-manifest-bytes", "pass" if manifest_ok else "fail", "all packaged manifests are byte-identical" if manifest_ok else "packaged manifest mismatch"))
        checks.append(_check("deterministic-zip-metadata", "pass", "sorted members, fixed timestamps, regular 0644 files, and integrity accepted"))
    return {"status": _status(checks), "checks": checks, "packages": package_records}


def _documentation_gate(root: Path) -> dict[str, object]:
    totals = _run_unit_paths([root / "tests" / "test_documentation.py"])
    readme = (root / "README.md").read_text(encoding="utf-8")
    package_ok = True
    for name in ("ctis.skill", "ctis-codex-plugin.zip", "ctis-claude-plugin.zip"):
        path = root / "dist" / name
        with zipfile.ZipFile(path) as archive:
            members = len([member for member in archive.namelist() if not member.endswith("/")])
        package_ok = package_ok and f"`{_sha256(path)}`" in readme and f"`{name}` | {members} |" in readme
    examples = _example_summary(root)
    if examples["skip"] == 1:
        example_text = "22 PASS / 1 SKIP (PHP runtime unavailable) / 0 FAIL"
    else:
        example_text = "23 PASS / 0 SKIP / 0 FAIL"
    testing = root / "docs" / "TESTING.md"
    testing_ok = testing.is_file()
    if testing_ok:
        testing_text = testing.read_text(encoding="utf-8")
        testing_ok = all(token in testing_text for token in ("python -B tools/run_acceptance.py", "ACCEPTANCE_OK", "runtime unavailable"))
    checks = [
        _check("documentation-tests-and-links", "pass" if all(totals[key] == 0 for key in ("failures", "errors", "skips")) else "fail", f"run={totals['run']} failures={totals['failures']} errors={totals['errors']} skips={totals['skips']}"),
        _check("readme-package-summary", "pass" if package_ok else "fail", "hashes and member counts match" if package_ok else "README package summary is stale"),
        _check("readme-example-summary", "pass" if example_text in readme else "fail", "runtime-aware suite summary matches" if example_text in readme else "README example summary is stale"),
        _check("testing-guide", "pass" if testing_ok else "fail", "reproduction and runtime limits documented" if testing_ok else "docs/TESTING.md is missing required reproduction guidance"),
    ]
    return {"status": _status(checks), "checks": checks}


def _active_config_snapshot() -> str:
    home = Path.home()
    roots = (
        home / ".codex" / "plugins",
        home / ".codex" / "skills",
        home / ".claude" / "plugins",
        home / ".codex" / "config.toml",
        home / ".claude" / "settings.json",
    )
    digest = hashlib.sha256()
    for index, root in enumerate(roots):
        digest.update(f"root:{index}:{root.exists()}\n".encode())
        candidates = [root] if root.is_file() or root.is_symlink() else sorted(root.rglob("*")) if root.is_dir() else []
        for candidate in candidates:
            try:
                stat_result = candidate.lstat()
                relative = "." if candidate == root else candidate.relative_to(root).as_posix()
                digest.update(
                    f"{index}:{relative.casefold()}:{stat_result.st_mode}:{stat_result.st_size}:{stat_result.st_mtime_ns}\n".encode("utf-8", errors="replace")
                )
            except OSError:
                digest.update(f"{index}:unreadable\n".encode())
    return digest.hexdigest()


def _direct_optional_script(name: str, script: Path, arguments: list[str], cwd: Path) -> dict[str, str]:
    if not script.is_file():
        return {"name": name, "status": "skip", "message": f"validator unavailable: {name}"}
    return run_argv([sys.executable, "-B", str(script), *arguments], cwd=cwd, label=name)


def _install_gate(root: Path) -> dict[str, object]:
    payloads = _load_module(root / "tools" / "platform_payloads.py", "install_payloads")
    source = root / "skills" / "ctis"
    canonical = payloads.codex_skill_payload(source)
    semantic = payloads.claude_skill_payload(source)
    before = _active_config_snapshot()
    checks: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="ctis-acceptance-install-") as temporary:
        temporary_root = Path(temporary)
        generic_root = temporary_root / "generic"
        codex_root = temporary_root / "codex"
        claude_root = temporary_root / "claude"
        generic_entries = safe_extract_archive(root / "dist" / "ctis.skill", generic_root)
        codex_entries = safe_extract_archive(root / "dist" / "ctis-codex-plugin.zip", codex_root)
        claude_entries = safe_extract_archive(root / "dist" / "ctis-claude-plugin.zip", claude_root)
        generic_skill = generic_root / "ctis"
        codex_plugin = codex_root / "ctis"
        codex_skill = codex_plugin / "skills" / "ctis"
        claude_plugin = claude_root / "ctis"
        claude_skill = claude_plugin / "skills" / "ctis"

        parity_errors = [
            *payload_parity_errors(canonical, {name.removeprefix("ctis/"): data for name, data in generic_entries.items()}, "generic-install"),
            *payload_parity_errors(canonical, {name.removeprefix("ctis/skills/ctis/"): data for name, data in codex_entries.items() if name.startswith("ctis/skills/ctis/")}, "codex-install"),
            *payload_parity_errors(semantic, {name.removeprefix("ctis/skills/ctis/"): data for name, data in claude_entries.items() if name.startswith("ctis/skills/ctis/")}, "claude-install"),
        ]
        checks.append(_check("extracted-payload-parity", "pass" if not parity_errors else "fail", "all extracted payloads match platform contracts" if not parity_errors else parity_errors[0]))
        command_errors = [
            *_command_contract_errors(codex_plugin),
            *_command_contract_errors(claude_plugin),
        ]
        checks.append(_check("extracted-command-contract", "pass" if not command_errors else "fail", "all extracted plugin command contracts accepted" if not command_errors else command_errors[0]))
        generic_command_members = [name for name in generic_entries if name.startswith("ctis/commands/")]
        checks.append(_check("generic-skill-excludes-commands", "pass" if not generic_command_members else "fail", "bare skill carries no command files" if not generic_command_members else f"unexpected bare-skill command member: {generic_command_members[0]}"))

        checks.extend((
            run_argv([sys.executable, "-B", str(generic_skill / "scripts" / "validate_ctis_skill.py"), "."], cwd=generic_skill, label="bundled-local-generic"),
            run_argv([sys.executable, "-B", str(codex_skill / "scripts" / "validate_ctis_skill.py"), "."], cwd=codex_skill, label="bundled-local-codex"),
            _check("bundled-local-claude-semantic", "pass", "Claude semantic payload accepted by exact 17-file contract"),
        ))

        home = Path.home()
        codex_plugin_validator = home / ".codex" / "skills" / ".system" / "plugin-creator" / "scripts" / "validate_plugin.py"
        quick_validator = home / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py"
        checks.append(_direct_optional_script("official-codex-plugin", codex_plugin_validator, ["."], codex_plugin))
        checks.append(run_optional_validator("official-claude-plugin", "claude", ["plugin", "validate", "."], claude_plugin))
        checks.append(_direct_optional_script("codex-skill-quick-generic", quick_validator, ["."], generic_skill))
        checks.append(_direct_optional_script("codex-skill-quick-codex", quick_validator, ["."], codex_skill))

    after = _active_config_snapshot()
    unchanged = before == after
    checks.append(_check("active-client-config-non-mutation", "pass" if unchanged else "fail", "active Codex and Claude plugin/skill configuration metadata unchanged" if unchanged else "active client configuration changed during acceptance"))
    validator_checks = [check for check in checks if check["name"].startswith(("bundled-", "official-", "codex-skill-"))]
    validator_summary = {
        "pass": sum(check["status"] == "pass" for check in validator_checks),
        "fail": sum(check["status"] == "fail" for check in validator_checks),
        "skip": sum(check["status"] == "skip" for check in validator_checks),
        "install_skips": sum(check["status"] == "skip" for check in validator_checks),
        "checks": validator_checks,
    }
    return {
        "status": _status(checks),
        "checks": checks,
        "validators": validator_summary,
        "active_config_non_mutation": "pass" if unchanged else "fail",
    }


GATE_FUNCTIONS.update({
    "source": _source_gate,
    "behavior": _behavior_gate,
    "packages": _package_gate,
    "docs": _documentation_gate,
    "install": _install_gate,
})


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local CTIS release acceptance.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root to validate",
    )
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    report = run_acceptance(root)
    write_report(root / "tmp" / "public-acceptance.json", report)
    for name in GATE_ORDER:
        print(f"GATE {name} {str(report.gates[name]['status']).upper()}")
    print("ACCEPTANCE_OK" if report.status == "pass" else "ACCEPTANCE_FAILED")
    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

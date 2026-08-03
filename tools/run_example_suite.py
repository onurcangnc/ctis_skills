from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath


MAX_OUTPUT_BYTES = 16_384
COMMAND_TIMEOUT_SECONDS = 15.0
PROBE_TIMEOUT_SECONDS = 2.0
CANONICAL_COURSES = {
    "CTIS151", "CTIS163", "CTIS164", "CTIS166", "CTIS255", "CTIS256",
    "CTIS259", "CTIS262", "CTIS264", "CTIS359", "CTIS411", "CTIS465",
    "CTIS474",
}
RECORD_FIELDS = {
    "id", "courses", "prompt", "artifact_paths", "verify", "expected",
    "runtime_required", "instructor_refs",
}
RUNTIME_NAME_RE = re.compile(r"^[A-Za-z0-9_.+-]+$")
SHELL_META_TOKENS = {"&", "&&", "|", "||", ";", ">", ">>", "<", "<<"}
SHELL_REDIRECTION_RE = re.compile(r"(?:^|[0-9])[<>]{1,2}")


class ExampleDeclarationError(ValueError):
    """An example declaration is malformed or crosses a trust boundary."""


@dataclass(frozen=True)
class ExampleResult:
    id: str
    passed: bool
    skipped: bool
    output: str
    reason: str


def _git_bash_candidates() -> list[Path]:
    if os.name != "nt":
        return []
    candidates: list[Path] = []
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(variable)
        if base:
            candidates.append(Path(base) / "Git" / "bin" / "bash.exe")
    candidates.append(Path("C:" + "/Program Files/Git/bin/bash.exe"))
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _runtime_works(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        completed = subprocess.run(
            [str(path), "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def find_runtime(name: str) -> str | None:
    """Resolve and health-check an executable without trusting PATH existence alone."""
    if name == "python":
        candidate = Path(sys.executable)
        return str(candidate) if _runtime_works(candidate) else None

    candidates: list[Path] = []
    discovered = shutil.which(name)
    if discovered:
        candidates.append(Path(discovered))
    if name == "bash":
        candidates.extend(_git_bash_candidates())

    checked: set[str] = set()
    for candidate in candidates:
        key = str(candidate).casefold()
        if key in checked:
            continue
        checked.add(key)
        if _runtime_works(candidate):
            return str(candidate)
    return None


def _contains_symlink(path: Path, stop: Path) -> bool:
    current = path
    while True:
        if current.is_symlink():
            return True
        if current == stop:
            return False
        if stop not in current.parents:
            return True
        current = current.parent


def _safe_manifest_relative(value: str, label: str) -> Path:
    if not value or "\x00" in value:
        raise ExampleDeclarationError(f"{label}: path must be a non-empty string")
    windows = PureWindowsPath(value)
    posix = PurePosixPath(value.replace("\\", "/"))
    if (
        windows.anchor
        or windows.drive
        or windows.root
        or windows.is_absolute()
        or posix.anchor
        or posix.root
        or posix.is_absolute()
        or ".." in windows.parts
        or ".." in posix.parts
    ):
        raise ExampleDeclarationError(f"{label}: value must be a portable relative path")
    return Path(*posix.parts)


def _validate_command(argv: object, label: str) -> list[str]:
    if not isinstance(argv, list) or not argv:
        raise ExampleDeclarationError(f"{label}: verify must be a non-empty argv array")
    if not all(isinstance(arg, str) and arg for arg in argv):
        raise ExampleDeclarationError(f"{label}: every argv value must be a non-empty string")
    for arg in argv:
        if (
            arg in SHELL_META_TOKENS
            or SHELL_REDIRECTION_RE.search(arg)
            or "$(" in arg
            or "`" in arg
        ):
            raise ExampleDeclarationError(f"{label}: shell syntax is forbidden")
        _safe_manifest_relative(arg, label)
    return argv


def _load_records(root: Path) -> tuple[Path, list[dict[str, object]]]:
    examples_root = root.resolve() / "examples"
    index_path = examples_root / "index.json"
    if _contains_symlink(index_path, examples_root):
        raise ExampleDeclarationError("examples/index.json: symbolic links are forbidden")
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExampleDeclarationError(f"examples/index.json: invalid index ({error})") from error
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "examples"}:
        raise ExampleDeclarationError("examples/index.json: expected schema_version and examples")
    if payload["schema_version"] != 1 or not isinstance(payload["examples"], list):
        raise ExampleDeclarationError("examples/index.json: unsupported schema")

    records: list[dict[str, object]] = []
    ids: set[str] = set()
    for position, raw in enumerate(payload["examples"]):
        label = f"examples[{position}]"
        if not isinstance(raw, dict) or set(raw) != RECORD_FIELDS:
            raise ExampleDeclarationError(f"{label}: record fields do not match schema")
        example_id = raw["id"]
        if not isinstance(example_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", example_id):
            raise ExampleDeclarationError(f"{label}: id must be a lowercase slug")
        if example_id in ids:
            raise ExampleDeclarationError(f"{label}: duplicate id {example_id}")
        ids.add(example_id)

        courses = raw["courses"]
        if (
            not isinstance(courses, list) or not courses
            or len(courses) != len(set(courses))
            or not all(isinstance(course, str) and course in CANONICAL_COURSES for course in courses)
        ):
            raise ExampleDeclarationError(f"{label}: invalid courses")
        if not isinstance(raw["prompt"], str) or not raw["prompt"].strip():
            raise ExampleDeclarationError(f"{label}: prompt is required")
        if not isinstance(raw["expected"], str) or len(raw["expected"].encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise ExampleDeclarationError(f"{label}: expected output is invalid or too large")
        runtime = raw["runtime_required"]
        if not isinstance(runtime, str) or not RUNTIME_NAME_RE.fullmatch(runtime):
            raise ExampleDeclarationError(f"{label}: runtime_required must be an executable name")
        refs = raw["instructor_refs"]
        if not isinstance(refs, list) or len(refs) != len(set(refs)) or not all(isinstance(ref, str) and ref for ref in refs):
            raise ExampleDeclarationError(f"{label}: instructor_refs must be unique strings")

        artifact_values = raw["artifact_paths"]
        if not isinstance(artifact_values, list) or not artifact_values:
            raise ExampleDeclarationError(f"{label}: artifact_paths must be a non-empty list")
        if len(artifact_values) != len(set(artifact_values)):
            raise ExampleDeclarationError(f"{label}: duplicate artifact declaration")
        for artifact_value in artifact_values:
            if not isinstance(artifact_value, str):
                raise ExampleDeclarationError(f"{label}: artifact path must be a string")
            relative = _safe_manifest_relative(artifact_value, label)
            artifact = examples_root / relative
            if _contains_symlink(artifact, examples_root):
                raise ExampleDeclarationError(f"{label}: symbolic-link artifacts are forbidden")
            if not artifact.is_file():
                raise ExampleDeclarationError(f"{label}: missing artifact {artifact_value}")
        _validate_command(raw["verify"], label)
        records.append(raw)
    return examples_root, records


def _execute(argv: list[str], cwd: Path) -> tuple[int | None, bytes, str | None]:
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
        )
    except OSError as error:
        return None, b"", f"could not start command: {error}"

    output = bytearray()
    overflow = threading.Event()

    def drain() -> None:
        assert process.stdout is not None
        while True:
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            remaining = MAX_OUTPUT_BYTES - len(output)
            if remaining > 0:
                output.extend(chunk[:remaining])
            if len(chunk) > remaining:
                overflow.set()
                process.kill()
                break

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    try:
        process.wait(timeout=COMMAND_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        reader.join(timeout=1)
        if process.stdout is not None:
            process.stdout.close()
        return process.returncode, bytes(output), f"timed out after {COMMAND_TIMEOUT_SECONDS:g}s"
    reader.join(timeout=1)
    if process.stdout is not None:
        process.stdout.close()
    if overflow.is_set():
        return process.returncode, bytes(output), f"output limit exceeded ({MAX_OUTPUT_BYTES} bytes)"
    return process.returncode, bytes(output), None


def run_examples(root: Path, strict: bool) -> list[ExampleResult]:
    del strict  # Declaration and execution semantics are equally strict in library use.
    examples_root, records = _load_records(root)
    results: list[ExampleResult] = []
    for record in records:
        example_id = str(record["id"])
        runtime_name = str(record["runtime_required"])
        runtime_path = find_runtime(runtime_name)
        if runtime_path is None:
            results.append(ExampleResult(example_id, False, True, "", f"runtime unavailable: {runtime_name}"))
            continue

        argv = list(record["verify"])
        executable_name = argv[0]
        if executable_name == runtime_name:
            executable = runtime_path
        else:
            executable = find_runtime(executable_name)
            if executable is None:
                results.append(
                    ExampleResult(
                        example_id, False, False, "",
                        f"undeclared runtime unavailable: {executable_name}",
                    )
                )
                continue
        resolved = [executable, *[runtime_path if value == "{runtime}" else value for value in argv[1:]]]
        returncode, raw_output, execution_error = _execute(resolved, examples_root)
        output = raw_output.decode("utf-8", errors="replace").replace("\r\n", "\n")
        if execution_error:
            results.append(ExampleResult(example_id, False, False, output, execution_error))
        elif returncode != 0:
            results.append(ExampleResult(example_id, False, False, output, f"exit code {returncode}"))
        elif output != record["expected"]:
            results.append(ExampleResult(example_id, False, False, output, "output mismatch"))
        else:
            results.append(ExampleResult(example_id, True, False, output, "verified"))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run public CTIS examples safely.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict-available", action="store_true")
    arguments = parser.parse_args()
    try:
        results = run_examples(arguments.root, strict=arguments.strict_available)
    except ExampleDeclarationError as error:
        print(f"DECLARATION ERROR: {error}")
        return 2

    passed = sum(result.passed for result in results)
    skipped = sum(result.skipped for result in results)
    failed = len(results) - passed - skipped
    for result in results:
        state = "PASS" if result.passed else "SKIP" if result.skipped else "FAIL"
        print(f"{state} {result.id}: {result.reason}")
    print(f"SUMMARY pass={passed} skip={skipped} fail={failed}")
    return 1 if failed and arguments.strict_available else 0


if __name__ == "__main__":
    raise SystemExit(main())

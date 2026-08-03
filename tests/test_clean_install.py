from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
import warnings
import zipfile
import contextlib
import io
import json
from pathlib import Path
from unittest import mock

from tools import run_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]

# The public-tree audit scans this file's own bytes once it is tracked. These
# fixtures are assembled at import time so the literal credential assignment and
# drive-rooted path never appear in the source, while the runtime values the
# redaction and extraction tests exercise stay exactly the same.
CREDENTIAL_FIXTURE = "OPENAI_API" + "_KEY" + "=" + "hunter2"
DRIVE_ROOTED_MEMBER = "C:" + "/drive-rooted"


class AcceptanceCliContractTests(unittest.TestCase):
    def test_cli_is_an_executable_acceptance_entry_point(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "tools" / "run_acceptance.py"), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("local CTIS release acceptance", result.stdout)

    def test_cli_writes_complete_report_and_emits_final_success_line(self) -> None:
        report = acceptance.AcceptanceReport(
            status="pass",
            gates={name: {"status": "pass", "checks": []} for name in acceptance.GATE_ORDER},
        )
        output = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["run_acceptance.py", "--root", str(ROOT)]),
            mock.patch.object(acceptance, "run_acceptance", return_value=report) as run,
            mock.patch.object(acceptance, "write_report") as write,
            contextlib.redirect_stdout(output),
        ):
            try:
                returncode = acceptance.main()
            except SystemExit as error:
                returncode = error.code

        self.assertEqual(0, returncode)
        run.assert_called_once_with(ROOT.resolve())
        write.assert_called_once_with(ROOT / "tmp" / "public-acceptance.json", report)
        self.assertEqual("ACCEPTANCE_OK", output.getvalue().splitlines()[-1])


class AcceptanceReportContractTests(unittest.TestCase):
    def test_report_has_exact_five_gates_and_propagates_failure(self) -> None:
        run_acceptance = getattr(acceptance, "run_acceptance", None)
        self.assertTrue(callable(run_acceptance), "run_acceptance(root) is required")
        names = ("source", "behavior", "packages", "docs", "install")

        def passed(_root: Path) -> dict[str, object]:
            return {"status": "pass", "checks": [{"name": "fixture", "status": "pass"}]}

        runners = {name: passed for name in names}
        runners["packages"] = lambda _root: {
            "status": "fail",
            "checks": [{"name": "byte-parity", "status": "fail", "message": "mismatch"}],
        }
        with mock.patch.object(acceptance, "GATE_FUNCTIONS", runners, create=True):
            report = run_acceptance(ROOT)

        payload = report.to_dict()
        self.assertEqual(1, payload["schema_version"])
        self.assertEqual("fail", payload["status"])
        self.assertEqual(list(names), list(payload["gates"]))
        self.assertEqual("fail", payload["gates"]["packages"]["status"])
        self.assertNotIn("timestamp", payload)

    def test_a_gate_that_mutates_the_checkout_fails_the_whole_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake_root = Path(temporary)
            (fake_root / "README.md").write_text("original", encoding="utf-8")

            def clean(_root: Path) -> dict[str, object]:
                return {"status": "pass", "checks": []}

            def mutating(root: Path) -> dict[str, object]:
                (root / "README.md").write_text("mutated", encoding="utf-8")
                return {"status": "pass", "checks": []}

            runners = {name: clean for name in acceptance.GATE_ORDER}
            with mock.patch.object(acceptance, "GATE_FUNCTIONS", runners):
                clean_payload = acceptance.run_acceptance(fake_root).to_dict()

            runners["packages"] = mutating
            with mock.patch.object(acceptance, "GATE_FUNCTIONS", runners):
                payload = acceptance.run_acceptance(fake_root).to_dict()

        self.assertEqual("pass", clean_payload["status"])
        self.assertEqual("pass", clean_payload["source_checkout_non_mutation"])
        self.assertEqual("fail", payload["status"])
        self.assertEqual("fail", payload["source_checkout_non_mutation"])
        self.assertTrue(all(gate["status"] == "pass" for gate in payload["gates"].values()))

    def test_gate_failure_text_is_redacted_before_entering_report(self) -> None:
        secret_message = f"{ROOT.resolve()} {CREDENTIAL_FIXTURE}"

        def exposed(_root: Path) -> dict[str, object]:
            return {
                "status": "fail",
                "checks": [{"name": "fixture", "status": "fail", "message": secret_message}],
            }

        with mock.patch.object(
            acceptance,
            "GATE_FUNCTIONS",
            {name: exposed for name in acceptance.GATE_ORDER},
        ):
            payload = acceptance.run_acceptance(ROOT).to_dict()

        serialized = json.dumps(payload)
        self.assertNotIn(str(ROOT.resolve()), serialized)
        self.assertNotIn("hunter2", serialized)
        self.assertIn("<repository> [REDACTED]", serialized)


def _process_is_alive(pid: int) -> bool:
    if os.name == "nt":
        listing = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return str(pid) in listing.stdout
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _archive(path: Path, members: list[tuple[str, bytes, int]]) -> None:
    with zipfile.ZipFile(path, "w") as output:
        for name, payload, mode in members:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = mode << 16
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                output.writestr(info, payload)


class SafeExtractionTests(unittest.TestCase):
    def test_rejects_unsafe_paths_and_member_kinds_before_writing(self) -> None:
        extract = getattr(acceptance, "safe_extract_archive", None)
        self.assertTrue(callable(extract), "safe_extract_archive is required")
        unsafe = (
            ("../escape", 0o100644),
            ("/rooted", 0o100644),
            ("C:drive-relative", 0o100644),
            (DRIVE_ROOTED_MEMBER, 0o100644),
            ("//server/share", 0o100644),
            (r"\\?\C:\device", 0o100644),
            ("folder/", 0o040755),
            ("link", 0o120777),
            ("fifo", 0o010644),
        )
        for name, mode in unsafe:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "unsafe.zip"
                destination = root / "out"
                _archive(source, [(name, b"unsafe", mode)])

                with self.assertRaises(acceptance.AcceptanceError):
                    extract(source, destination)

                self.assertFalse(destination.exists() and any(destination.rglob("*")))

    def test_rejects_collisions_permissions_and_size_before_any_write(self) -> None:
        mutations = (
            [("one.txt", b"a", 0o100644), ("one.txt", b"b", 0o100644)],
            [("Case.txt", b"a", 0o100644), ("case.txt", b"b", 0o100644)],
            [("writable.txt", b"a", 0o100666)],
            [("large.txt", b"abcd", 0o100644)],
        )
        for index, members in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "mutation.zip"
                destination = root / "out"
                _archive(source, [("safe.txt", b"safe", 0o100644), *members])

                kwargs = {"max_member_bytes": 3} if index == 3 else {}
                with self.assertRaises(acceptance.AcceptanceError):
                    acceptance.safe_extract_archive(source, destination, **kwargs)

                self.assertFalse(destination.exists())

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "total.zip"
            _archive(
                source,
                [("one.txt", b"abc", 0o100644), ("two.txt", b"def", 0o100644)],
            )
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.safe_extract_archive(
                    source,
                    root / "out",
                    max_member_bytes=4,
                    max_total_bytes=5,
                )
            self.assertFalse((root / "out").exists())

    def test_rejects_corruption_and_returns_exact_clean_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corrupt = root / "corrupt.zip"
            corrupt.write_bytes(b"not a zip archive")
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.safe_extract_archive(corrupt, root / "bad-out")

            clean = root / "clean.zip"
            _archive(clean, [("root/file.txt", b"payload", 0o100644)])
            destination = root / "clean-out"
            payload = acceptance.safe_extract_archive(clean, destination)

            self.assertEqual({"root/file.txt": b"payload"}, payload)
            self.assertEqual(b"payload", (destination / "root" / "file.txt").read_bytes())


class BoundedProcessTests(unittest.TestCase):
    def test_output_and_timeout_are_bounded_and_messages_are_redacted(self) -> None:
        run_argv = getattr(acceptance, "run_argv", None)
        self.assertTrue(callable(run_argv), "run_argv is required")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            noisy = run_argv(
                [sys.executable, "-c", "print('x' * 4096)"],
                cwd=root,
                label="noisy-validator",
                timeout=2,
                max_output_bytes=128,
            )
            slow = run_argv(
                [sys.executable, "-c", "import time; time.sleep(2)"],
                cwd=root,
                label="slow-validator",
                timeout=0.05,
                max_output_bytes=128,
            )
            exposed = acceptance.sanitize_message(
                f"{root.resolve()} {CREDENTIAL_FIXTURE}",
                replacements={str(root.resolve()): "<temporary>"},
            )

        self.assertEqual("fail", noisy["status"])
        self.assertIn("output limit exceeded", noisy["message"])
        self.assertLessEqual(len(noisy["message"].encode("utf-8")), 1024)
        self.assertEqual("fail", slow["status"])
        self.assertIn("timed out", slow["message"])
        self.assertEqual("<temporary> [REDACTED]", exposed)

    def test_protected_checkout_is_refused_as_a_subprocess_working_directory(self) -> None:
        with mock.patch.object(acceptance, "_PROTECTED_ROOT", ROOT):
            for cwd in (ROOT, ROOT / "tools"):
                with self.subTest(cwd=cwd), self.assertRaises(acceptance.AcceptanceError):
                    acceptance.run_argv([sys.executable, "-c", "pass"], cwd=cwd, label="guard")
            with tempfile.TemporaryDirectory() as temporary:
                allowed = acceptance.run_argv(
                    [sys.executable, "-c", "pass"], cwd=Path(temporary), label="guard", timeout=10
                )

        self.assertEqual("pass", allowed["status"])

    def test_timed_out_child_and_its_grandchildren_are_all_terminated(self) -> None:
        spawner = (
            "import subprocess, sys, time;"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']);"
            "print(child.pid, flush=True); time.sleep(30)"
        )
        with tempfile.TemporaryDirectory() as temporary:
            returncode, output, error = acceptance._execute_argv(
                [sys.executable, "-B", "-c", spawner],
                cwd=Path(temporary),
                timeout=3,
                max_output_bytes=1024,
            )

        self.assertIsNotNone(error)
        self.assertIn("timed out", str(error))
        grandchild = int(output.decode("utf-8").strip())
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and _process_is_alive(grandchild):
            time.sleep(0.1)
        self.assertFalse(_process_is_alive(grandchild), "grandchild survived the timeout kill")

    def test_optional_validator_absence_is_named_skip_and_failure_is_not_hidden(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unavailable_discovery = mock.Mock(return_value=None)
            unavailable = acceptance.run_optional_validator(
                "optional-tool", "missing-tool", ["--check"], root,
                discover=unavailable_discovery,
            )
            failing = acceptance.run_optional_validator(
                "optional-tool", "python", ["-c", "raise SystemExit(7)"], root,
                discover=mock.Mock(return_value=sys.executable),
            )

        self.assertEqual(
            {"name": "optional-tool", "status": "skip", "message": "validator unavailable: missing-tool"},
            unavailable,
        )
        self.assertEqual("fail", failing["status"])
        self.assertIn("exit code 7", failing["message"])


class AcceptanceInfrastructureTests(unittest.TestCase):
    def test_unit_subtotal_explicitly_excludes_only_acceptance_module(self) -> None:
        discover = getattr(acceptance, "unit_test_modules", None)
        self.assertTrue(callable(discover), "unit_test_modules is required")
        actual = discover(ROOT)
        expected = sorted(
            path for path in (ROOT / "tests").glob("test_*.py")
            if path.name != "test_clean_install.py"
        )

        self.assertEqual(expected, actual)
        self.assertNotIn(ROOT / "tests" / "test_clean_install.py", actual)

    def test_this_module_itself_satisfies_the_public_tree_audit(self) -> None:
        audit = acceptance._load_module(ROOT / "tools" / "audit_public_tree.py", "audit_self")
        relative = Path(__file__).resolve().relative_to(ROOT).as_posix()

        self.assertEqual([], audit.audit_public_tree(ROOT, [relative]))

    def test_isolated_success_and_failure_preserve_checkout_inventory_and_bytes(self) -> None:
        isolate = getattr(acceptance, "run_isolated_checkout", None)
        fingerprint = getattr(acceptance, "checkout_fingerprint", None)
        self.assertTrue(callable(isolate), "run_isolated_checkout is required")
        self.assertTrue(callable(fingerprint), "checkout_fingerprint is required")
        before = fingerprint(ROOT)

        def mutate_success(isolated: Path) -> str:
            (isolated / "README.md").write_text("changed", encoding="utf-8")
            work = isolated / "examples" / ".runtime-work"
            work.mkdir(parents=True)
            (work / "generated.bin").write_bytes(b"generated")
            return "ok"

        self.assertEqual("ok", isolate(ROOT, mutate_success))
        self.assertEqual(before, fingerprint(ROOT))

        def mutate_failure(isolated: Path) -> None:
            (isolated / "README.md").write_text("failed", encoding="utf-8")
            work = isolated / "examples" / ".runtime-work"
            work.mkdir(parents=True)
            (work / "partial.bin").write_bytes(b"partial")
            raise RuntimeError("injected isolated failure")

        with self.assertRaisesRegex(RuntimeError, "injected isolated failure"):
            isolate(ROOT, mutate_failure)
        self.assertEqual(before, fingerprint(ROOT))

    def test_machine_report_replacement_is_transactional_and_stable(self) -> None:
        writer = getattr(acceptance, "write_report", None)
        self.assertTrue(callable(writer), "write_report is required")
        report = acceptance.AcceptanceReport(
            status="pass",
            gates={
                name: {"status": "pass", "checks": []}
                for name in acceptance.GATE_ORDER
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "public-acceptance.json"
            target.write_bytes(b"original")

            def fail_replace(_source: Path, _target: Path) -> None:
                raise OSError("injected replacement failure")

            with self.assertRaises(OSError):
                writer(target, report, replace=fail_replace)
            self.assertEqual(b"original", target.read_bytes())
            self.assertEqual([], list(target.parent.glob(".public-acceptance.json.*.tmp")))

            writer(target, report)
            first = target.read_bytes()
            writer(target, report)
            second = target.read_bytes()

        self.assertEqual(first, second)
        self.assertEqual(report.to_dict(), json.loads(first.decode("utf-8")))
        self.assertTrue(first.endswith(b"\n"))


class PayloadParityTests(unittest.TestCase):
    def test_payload_omission_and_byte_mutation_are_rejected(self) -> None:
        verify = getattr(acceptance, "payload_parity_errors", None)
        self.assertTrue(callable(verify), "payload_parity_errors is required")
        expected = {"SKILL.md": b"skill", "references/course.md": b"course"}

        self.assertEqual([], verify(expected, dict(expected), "fixture"))
        self.assertEqual(
            ["fixture missing member: references/course.md"],
            verify(expected, {"SKILL.md": b"skill"}, "fixture"),
        )
        self.assertEqual(
            ["fixture byte mismatch: SKILL.md"],
            verify(expected, {**expected, "SKILL.md": b"changed"}, "fixture"),
        )


class FullAcceptanceTests(unittest.TestCase):
    def test_repository_passes_all_five_clean_install_gates(self) -> None:
        before = acceptance.checkout_fingerprint(ROOT)
        report = acceptance.run_acceptance(ROOT)
        after = acceptance.checkout_fingerprint(ROOT)
        payload = report.to_dict()

        self.assertEqual(before, after)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(
            ["source", "behavior", "packages", "docs", "install"],
            list(payload["gates"]),
        )
        self.assertTrue(all(gate["status"] == "pass" for gate in payload["gates"].values()))
        self.assertGreater(payload["unit_totals"]["run"], 100)
        self.assertEqual(
            {"failures": 0, "errors": 0, "skips": 0},
            {key: payload["unit_totals"][key] for key in ("failures", "errors", "skips")},
        )
        self.assertEqual(0, payload["examples"]["fail"])
        self.assertIn(
            (payload["examples"]["pass"], payload["examples"]["skip"]),
            {(23, 1), (24, 0)},
        )
        self.assertEqual(
            {"ctis.skill": 19, "ctis-codex-plugin.zip": 34, "ctis-claude-plugin.zip": 35},
            {name: record["members"] for name, record in payload["packages"].items()},
        )
        self.assertEqual({"critical": 0, "important": 0}, payload["review_findings"])
        self.assertEqual(0, payload["validators"]["install_skips"])
        self.assertEqual("pass", payload["active_config_non_mutation"])
        self.assertEqual("pass", payload["source_checkout_non_mutation"])
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn(str(ROOT.resolve()), serialized)
        self.assertNotIn(str(Path.home().resolve()), serialized)


if __name__ == "__main__":
    unittest.main()

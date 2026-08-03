from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORK_ROOT = ROOT / ".runtime-work"


def run_checked(argv: list[str], *, cwd: Path, input_text: str | None = None) -> str:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"runtime command failed with {completed.returncode}: {completed.stdout[-1000:]}{completed.stderr[-1000:]}")
    return completed.stdout.replace("\r\n", "\n")


def check_c(compiler: str) -> None:
    work = WORK_ROOT / "ctis151"
    work.mkdir(parents=True)
    executable = work / ("sentinel_stats.exe" if sys.platform == "win32" else "sentinel_stats")
    run_checked(
        [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", str(ROOT / "ctis151" / "sentinel_stats.c"), "-o", str(executable)],
        cwd=ROOT,
    )
    assert run_checked([str(executable)], cwd=ROOT, input_text="20\nbad\n100\n-1\n30\n") == "INVALID\nCOUNT 2 AVERAGE 60.00\n"
    assert run_checked([str(executable)], cwd=ROOT, input_text="-2\n101\n-1\n") == "INVALID\nINVALID\nCOUNT 0\n"


def check_gpp(compiler: str) -> None:
    work = WORK_ROOT / "ctis164"
    work.mkdir(parents=True)
    executable = work / ("geometry.exe" if sys.platform == "win32" else "geometry")
    run_checked(
        [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", str(ROOT / "ctis164" / "geometry.cpp"), "-o", str(executable)],
        cwd=ROOT,
    )
    assert run_checked([str(executable)], cwd=ROOT) == "GEOMETRY_OK\n"


def check_dotnet(runtime: str) -> None:
    work = WORK_ROOT / "ctis465"
    work.mkdir(parents=True)
    for name in ("CatalogSlice.csproj", "NuGet.Config", "Program.cs"):
        shutil.copy2(ROOT / "ctis465" / name, work / name)
    project = work / "CatalogSlice.csproj"
    config = work / "NuGet.Config"
    packages = work / "packages"
    run_checked([runtime, "restore", str(project), "--configfile", str(config), "--packages", str(packages)], cwd=work)
    output = run_checked([runtime, "run", "--no-restore", "--project", str(project), f"-p:RestorePackagesPath={packages}"], cwd=work)
    assert output == "DOTNET_SLICE_OK\n"


CHECKS = {"c": check_c, "g++": check_gpp, "dotnet": check_dotnet}


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in CHECKS:
        return 2
    try:
        CHECKS[sys.argv[1]](sys.argv[2])
        print(f"RUNTIME_OK {sys.argv[1]}")
        return 0
    finally:
        shutil.rmtree(WORK_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

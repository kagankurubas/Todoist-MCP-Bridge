"""Installs the built wheel into a throwaway venv and runs the installed-mode tests against it.

Usage: python scripts/run_installed_tests.py <dist directory>

Steps, each failing the run on error:
1. Takes the single wheel in the dist directory and prints its name and sha256.
2. Creates a venv in a new temporary directory outside the checkout and installs
   `<wheel>[test]` into it.
3. Isolation proof: that venv's `python -I`, started from the temporary directory, must import
   `plugvan` from its own site-packages.
4. Runs ONLY the installed-mode test modules with that venv's
   `python -I -m pytest --import-mode=importlib`, from the temporary directory, so neither the
   working directory nor pytest puts the checkout on sys.path. PLUGVAN_INSTALLED_VENV tells the
   tests which venv to check; PLUGVAN_TEST_SERVER_COMMAND points the STDIO test from #60 at the
   installed `plugvan-mcp todoist`. The full suite is never run here: some of its tests read
   source files by repository path.
5. Fails unless at least one test ran and none was skipped, so a lost variable cannot turn the
   run into a silent pass.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
import xml.etree.ElementTree as ElementTree
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLED_TEST_PATHS = [
    REPO_ROOT / "tests" / "installed",
    REPO_ROOT / "tests" / "todoist" / "test_server_stdio.py",
]
ISOLATION_PROOF = (
    "import pathlib, sys, sysconfig, plugvan\n"
    "site = pathlib.Path(sysconfig.get_paths()['purelib']).resolve()\n"
    "module = pathlib.Path(plugvan.__file__).resolve()\n"
    "assert site in module.parents, f'plugvan imported from {module}, not from {site}'\n"
    "print(f'plugvan imported from {module}')\n"
)


def _run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: run_installed_tests.py <dist directory>", file=sys.stderr)
        return 2
    wheels = sorted(Path(argv[0]).resolve().glob("*.whl"))
    if len(wheels) != 1:
        print(f"expected exactly one wheel in {argv[0]}, found {len(wheels)}", file=sys.stderr)
        return 1
    wheel = wheels[0]
    print(f"wheel: {wheel.name} sha256={hashlib.sha256(wheel.read_bytes()).hexdigest()}", flush=True)

    temp = Path(tempfile.mkdtemp(prefix="plugvan-installed-")).resolve()
    try:
        if REPO_ROOT in temp.parents:
            print(f"temporary directory {temp} is inside the checkout", file=sys.stderr)
            return 1
        venv_dir = temp / "venv"
        venv.create(venv_dir, with_pip=True)
        scripts = venv_dir / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        console_script = scripts / ("plugvan-mcp.exe" if os.name == "nt" else "plugvan-mcp")

        _run([str(python), "-m", "pip", "install", "--quiet", f"{wheel}[test]"], cwd=temp)
        _run([str(python), "-I", "-c", ISOLATION_PROOF], cwd=temp)

        junit = temp / "installed-tests.xml"
        env = {
            **os.environ,
            "PLUGVAN_INSTALLED_VENV": str(venv_dir),
            "PLUGVAN_TEST_SERVER_COMMAND": json.dumps([str(console_script), "todoist"]),
        }
        env.pop("PYTHONPATH", None)
        command = [
            str(python), "-I", "-m", "pytest", "--import-mode=importlib", "-p", "no:cacheprovider",
            "--rootdir", str(REPO_ROOT), f"--junitxml={junit}", "-v", "-rs",
            *[str(path) for path in INSTALLED_TEST_PATHS],
        ]
        print("$", " ".join(command), flush=True)
        returncode = subprocess.run(command, cwd=temp, env=env).returncode
        if returncode != 0:
            return returncode

        suite = ElementTree.parse(junit).getroot().find("testsuite")
        tests, skipped = int(suite.get("tests")), int(suite.get("skipped"))
        if tests == 0 or skipped:
            print(f"installed-mode run is not valid: {tests} tests, {skipped} skipped", file=sys.stderr)
            return 1
        return 0
    finally:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

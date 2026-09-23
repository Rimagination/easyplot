"""Run a UTF-8 R figure script without changing the parent or system locale.

Windows R >=4.2 uses UCRT locale names; inherited C.UTF-8 can corrupt source
before R can repair it. --library is optional and affects only this child.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess


def r_environment(library: str | None = None, *, windows: bool | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if os.name == "nt" if windows is None else windows:
        for key in ("LANG", "LC_ALL", "LC_CTYPE"):
            env[key] = "English_United States.UTF-8"
    if library:
        path = Path(library).resolve(strict=True)
        if not path.is_dir():
            raise ValueError("--library must be an existing directory")
        # Preserve other user libraries; R's separator is ';' on Windows.
        previous = env.get("R_LIBS_USER", "")
        env["R_LIBS_USER"] = str(path) + (os.pathsep + previous if previous else "")
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rscript", default=shutil.which("Rscript"))
    parser.add_argument("--library", help="existing task-specific R package library")
    parser.add_argument("script", type=Path, help="UTF-8 R script")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.rscript:
        parser.error("Rscript not found; supply --rscript")
    script = args.script.resolve(strict=True)
    # Fail on invalid UTF-8 instead of silently translating source bytes.
    script.read_text(encoding="utf-8-sig")
    return subprocess.run([args.rscript, "--vanilla", "--encoding=UTF-8", str(script), *args.args],
                          env=r_environment(args.library), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

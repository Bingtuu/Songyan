"""V12 Task 224d runner: REAL SMOKE using Writer card 1.1.1 + fixed coordinate regex.

Reuses the latest approved plan from 224c (v12_task224c_ch1_plan_115548).

Usage:
    python scripts/v12_224d_runner.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

SPEC_PATH = ROOT / "projects" / "hard-sf-new-weird" / "planning" / "supervision_spec.json"
RUNTIME_DB = ROOT / "projects" / "hard-sf-new-weird" / "runtime" / "songyan.db"
APPROVED_PLAN_PATH = (
    ROOT
    / "projects"
    / "hard-sf-new-weird"
    / "runs"
    / "v12_task224c_ch1_plan_115548"
    / "approved_plan_ch1.json"
)
PROJECT_ID = "hard-sf-new-weird-v12-224b-235415"
RUN_DIR = ROOT / "projects" / "hard-sf-new-weird" / "runs"


def gen_suffix() -> str:
    return time.strftime("%H%M%S", time.localtime())


def main() -> int:
    stamp = gen_suffix()
    print(f"[224d] V12 Task 224d Ch1-only real smoke - started at {stamp}")
    print(f"[224d] project_id        : {PROJECT_ID}")
    print(f"[224d] db                : {RUNTIME_DB}")
    print(f"[224d] supervision spec  : {SPEC_PATH}")
    print(f"[224d] approved plan     : {APPROVED_PLAN_PATH}")
    print(f"[224d] writer card       : 1.1.1 (5-layer beat contract)")

    # Environment: use Path.as_posix() with raw spaces (not %-encoded)
    os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
    os.environ["CHECKPOINTER_MODE"] = "sqlite"
    os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)
    os.environ["SONGYAN_STARTUP_APPROVED_PLAN"] = str(APPROVED_PLAN_PATH)

    print(f"[224d] env:DATABASE_URL  : {os.environ['DATABASE_URL']}")

    # Build run output dir
    run_out_dir = RUN_DIR / f"v12_task224d_ch1_real_{stamp}"
    run_out_dir.mkdir(parents=True, exist_ok=True)

    # Invoke via run_with_timeout wrapper
    wrapper = ROOT / "scripts" / "run_with_timeout.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-File",
        str(wrapper),
        "-TimeoutSec",
        "3600",
        "--",
        "songyan",
        "run",
        "--project-id",
        PROJECT_ID,
        "--chapters",
        "1",
        "--auto-confirm",
        "--on-failure",
        "isolate",
    ]
    print(f"\n[224d] Executing: {' '.join(cmd)}")
    print("=" * 60)

    proc = subprocess.run(cmd, cwd=str(ROOT))
    rc = proc.returncode
    print("=" * 60)
    print(f"[224d] completed with exit_code={rc}")
    print(f"[224d] post-process hints:")
    print(f"  songyan report --project-id {PROJECT_ID} --last-run")
    print(f"  songyan export --project-id {PROJECT_ID} --chapters 1 --format md --output projects/hard-sf-new-weird/exports/ch001_round_v12_224d/")
    print(f"  songyan bundle-run --run-id <run_id> --output projects/hard-sf-new-weird/bundles/")
    return rc


if __name__ == "__main__":
    sys.exit(main())

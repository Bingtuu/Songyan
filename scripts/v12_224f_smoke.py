"""V12 Task 224f smoke runner: Ch1-only REAL SMOKE on clean rebuilt project.

Uses the 224f approved plan (v12_task224f_ch1_plan_144113) and the Writer card
with per-beat word floor (e4ac420) and brief-level half-named-person ban (75ec0cf, 224f 选项 B).

Usage:
    python scripts/v12_224f_smoke.py
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
    / "v12_task224f_ch1_plan_144113"
    / "approved_plan_ch1.json"
)
PROJECT_ID = "hard-sf-new-weird-v12-224f-144113"
RUN_DIR = ROOT / "projects" / "hard-sf-new-weird" / "runs"


def gen_suffix() -> str:
    return time.strftime("%H%M%S", time.localtime())


def main() -> int:
    stamp = gen_suffix()
    print(f"[224f-smoke] V12 Task 224f Ch1-only real smoke - started at {stamp}")
    print(f"[224f-smoke] project_id        : {PROJECT_ID}")
    print(f"[224f-smoke] db                : {RUNTIME_DB}")
    print(f"[224f-smoke] supervision spec  : {SPEC_PATH}")
    print(f"[224f-smoke] approved plan     : {APPROVED_PLAN_PATH}")
    print("[224f-smoke] writer card       : 1.1.1 + per-beat floor + brief 半具名禁令 (75ec0cf)")

    os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
    os.environ["CHECKPOINTER_MODE"] = "sqlite"
    os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)
    os.environ["SONGYAN_STARTUP_APPROVED_PLAN"] = str(APPROVED_PLAN_PATH)

    run_out_dir = RUN_DIR / f"v12_task224f_ch1_real_{stamp}"
    run_out_dir.mkdir(parents=True, exist_ok=True)

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
    print(f"\n[224f-smoke] Executing: {' '.join(cmd)}")
    print("=" * 60)

    proc = subprocess.run(cmd, cwd=str(ROOT))
    rc = proc.returncode
    print("=" * 60)
    print(f"[224f-smoke] completed with exit_code={rc}")
    print("[224f-smoke] post-process hints:")
    print(f"  songyan report --project-id {PROJECT_ID} --last-run")
    print(
        f"  songyan export --project-id {PROJECT_ID} --chapters 1 --format md "
        "--output projects/hard-sf-new-weird/exports/ch001_round_v12_224f/"
    )
    print("  songyan bundle-run --run-id <run_id> --output projects/hard-sf-new-weird/bundles/")
    return rc


if __name__ == "__main__":
    sys.exit(main())

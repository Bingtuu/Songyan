"""V12 Task 225 smoke runner: Ch1-Ch3 REAL SMOKE on the 224f project.

Uses the Task 225 approved plan (latest runs/v12_task225_ch2_3_plan_*/
approved_plan_ch2_3.json) covering Ch2/Ch3. Ch1 is already accepted in the
project and is automatically skipped by the pipeline
(phase2_graph skip_accepted_chapters), so only Ch2/Ch3 are generated.

Usage:
    python scripts/v12_225_smoke.py
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
PROJECT_ID = "hard-sf-new-weird-v12-224f-144113"
RUN_DIR = ROOT / "projects" / "hard-sf-new-weird" / "runs"


def gen_suffix() -> str:
    return time.strftime("%H%M%S", time.localtime())


def find_latest_approved_plan() -> Path:
    candidates = sorted(RUN_DIR.glob("v12_task225_ch2_3_plan_*/approved_plan_ch2_3.json"))
    if not candidates:
        raise RuntimeError(
            "no approved_plan_ch2_3.json found under runs/v12_task225_ch2_3_plan_*/; "
            "run scripts/v12_225_runner.py first"
        )
    return candidates[-1]


def main() -> int:
    stamp = gen_suffix()
    approved_plan_path = find_latest_approved_plan()
    print(f"[225-smoke] V12 Task 225 Ch1-Ch3 real smoke - started at {stamp}")
    print(f"[225-smoke] project_id        : {PROJECT_ID}")
    print(f"[225-smoke] db                : {RUNTIME_DB}")
    print(f"[225-smoke] supervision spec  : {SPEC_PATH}")
    print(f"[225-smoke] approved plan     : {approved_plan_path}")
    print("[225-smoke] note: Ch1 already accepted -> auto-skipped; only Ch2/Ch3 generated")

    os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
    os.environ["CHECKPOINTER_MODE"] = "sqlite"
    os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)
    os.environ["SONGYAN_STARTUP_APPROVED_PLAN"] = str(approved_plan_path)

    run_out_dir = RUN_DIR / f"v12_task225_ch1_3_real_{stamp}"
    run_out_dir.mkdir(parents=True, exist_ok=True)

    wrapper = ROOT / "scripts" / "run_with_timeout.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-File",
        str(wrapper),
        "-TimeoutSec",
        "7200",
        "--",
        "songyan",
        "run",
        "--project-id",
        PROJECT_ID,
        "--chapters",
        "1-3",
        "--auto-confirm",
        "--on-failure",
        "isolate",
    ]
    print(f"\n[225-smoke] Executing: {' '.join(cmd)}")
    print("=" * 60)

    proc = subprocess.run(cmd, cwd=str(ROOT))
    rc = proc.returncode
    print("=" * 60)
    print(f"[225-smoke] completed with exit_code={rc}")
    print("[225-smoke] post-process hints:")
    print(f"  songyan report --project-id {PROJECT_ID} --last-run")
    print(
        f"  songyan export --project-id {PROJECT_ID} --chapters 1-3 --format md "
        "--output projects/hard-sf-new-weird/exports/ch001_003_round_v12_225/"
    )
    print("  songyan bundle-run --run-id <run_id> --output projects/hard-sf-new-weird/bundles/")
    return rc


if __name__ == "__main__":
    sys.exit(main())

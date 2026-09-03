"""V12 Task 225 smoke runner (round 2): Ch3-only REAL SMOKE after r3 override.

Ch1/Ch2 已 accepted（v-e9687c62 / v-d00dd445），本脚本只重跑 Ch3。
使用 round-3 覆写后的 approved plan（approved_plan_ch2_3.json，chapters=[2,3]，
Ch3 在覆盖范围内，approved-plan short-circuit 生效）。

Usage:
    python scripts/v12_225_smoke_ch3.py
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
    / "v12_task225_ch2_3_plan_200216"
    / "approved_plan_ch2_3.json"
)
PROJECT_ID = "hard-sf-new-weird-v12-224f-144113"


def main() -> int:
    stamp = time.strftime("%H%M%S", time.localtime())
    print(f"[225-smoke-ch3] V12 Task 225 Ch3-only real smoke (round 2) - {stamp}")
    print(f"[225-smoke-ch3] project_id        : {PROJECT_ID}")
    print(f"[225-smoke-ch3] approved plan     : {APPROVED_PLAN_PATH}")
    if not APPROVED_PLAN_PATH.exists():
        raise RuntimeError("approved plan missing; run scripts/v12_225_plan_override_r3.py first")

    os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
    os.environ["CHECKPOINTER_MODE"] = "sqlite"
    os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)
    os.environ["SONGYAN_STARTUP_APPROVED_PLAN"] = str(APPROVED_PLAN_PATH)

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
        "3",
        "--auto-confirm",
        "--on-failure",
        "isolate",
    ]
    print(f"\n[225-smoke-ch3] Executing: {' '.join(cmd)}")
    print("=" * 60)

    proc = subprocess.run(cmd, cwd=str(ROOT))
    rc = proc.returncode
    print("=" * 60)
    print(f"[225-smoke-ch3] completed with exit_code={rc}")
    print("[225-smoke-ch3] post-process hints:")
    print(f"  songyan report --project-id {PROJECT_ID} --last-run")
    print(
        f"  songyan export --project-id {PROJECT_ID} --chapters 1-3 --format md "
        "--output projects/hard-sf-new-weird/exports/ch001_003_round_v12_225/"
    )
    return rc


if __name__ == "__main__":
    sys.exit(main())

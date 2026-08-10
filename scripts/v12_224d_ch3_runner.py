"""V12 Task 224d Ch3 runner: REAL SMOKE for Chapter 3 with approved plan.

Uses Writer card 1.1.1 (5-layer beat contract) + fixed coordinate regex +
Ch3 supervision spec beats (introducing temporary object V-0003) with stable
numeric anchors carried forward from Ch2 (21.0 kg / 12.0 /min, no change this
chapter).

Ch3 uses an approved plan that locks the spec-beat-aligned ChapterGoal +
CreativeBrief (INSERTed in DB by v12_224d_ch3_plan_override.py). The
goal_planner_node and creative_director_node short-circuit when
SONGYAN_STARTUP_APPROVED_PLAN is set, skipping LLM planning and reusing the
INSERTed goal/brief.

This run verifies:
  1. Budget accumulation pressure: Ch3 loads Ch1+Ch2 summaries + Ch3 goal/brief
     with the new profile (base_budget=10500, ramp_per_chapter=300). Expected
     Ch3 budget = 10500 + 3×300 = 11400 tokens. Must NOT trigger ContextEmergency.
  2. Writer word count compliance: 5-layer beat contract should produce
     2700-3300 chars without ContextEmergency budget pruning.

Usage:
    python scripts/v12_224d_ch3_runner.py
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
# Use the latest approved_plan dir created by v12_224d_ch3_plan_override.py
_APPROVED_PLAN_DIRS = sorted(
    (ROOT / "projects" / "hard-sf-new-weird" / "runs").glob(
        "v12_task224d_ch3_plan_*/approved_plan_ch3.json"
    )
)
if not _APPROVED_PLAN_DIRS:
    print("ERROR: no approved_plan_ch3.json found. Run v12_224d_ch3_plan_override.py first.")
    sys.exit(2)
APPROVED_PLAN_PATH = _APPROVED_PLAN_DIRS[-1]
PROJECT_ID = "hard-sf-new-weird-v12-224b-235415"
RUN_DIR = ROOT / "projects" / "hard-sf-new-weird" / "runs"


def gen_suffix() -> str:
    return time.strftime("%H%M%S", time.localtime())


def main() -> int:
    stamp = gen_suffix()
    print(f"[224d-ch3] V12 Task 224d Ch3 real smoke (approved plan) - started at {stamp}")
    print(f"[224d-ch3] project_id        : {PROJECT_ID}")
    print(f"[224d-ch3] db                : {RUNTIME_DB}")
    print(f"[224d-ch3] supervision spec  : {SPEC_PATH}")
    print(f"[224d-ch3] approved plan     : {APPROVED_PLAN_PATH}")
    print(f"[224d-ch3] writer card       : 1.1.1 (5-layer beat contract)")
    print(f"[224d-ch3] numeric anchors   : unassigned_mass_delta 21.0 -> 21.0 kg (stable)")
    print(f"                                breath_rate 12.0 -> 12.0 /min (stable)")
    print(f"[224d-ch3] profile           : base_budget=10500, ramp_per_chapter=300")
    print(f"[224d-ch3] expected budget   : 10500 + 3*300 = 11400 tokens")
    print(f"[224d-ch3] plan lock         : goal_planner + creative_director short-circuit on approved_plan")

    # Environment: use Path.as_posix() with raw spaces (not %-encoded)
    os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
    os.environ["CHECKPOINTER_MODE"] = "sqlite"
    os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)
    os.environ["SONGYAN_STARTUP_APPROVED_PLAN"] = str(APPROVED_PLAN_PATH)

    print(f"[224d-ch3] env:DATABASE_URL  : {os.environ['DATABASE_URL']}")

    # Build run output dir
    run_out_dir = RUN_DIR / f"v12_task224d_ch3_real_{stamp}"
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
        "3",
        "--auto-confirm",
        "--on-failure",
        "isolate",
    ]
    print(f"\n[224d-ch3] Executing: {' '.join(cmd)}")
    print("=" * 60)

    proc = subprocess.run(cmd, cwd=str(ROOT))
    rc = proc.returncode
    print("=" * 60)
    print(f"[224d-ch3] completed with exit_code={rc}")
    print(f"[224d-ch3] post-process hints:")
    print(f"  songyan report --project-id {PROJECT_ID} --last-run")
    print(f"  songyan export --project-id {PROJECT_ID} --chapters 3 --format md --output projects/hard-sf-new-weird/exports/ch003_round_v12_224d/")
    print(f"  songyan bundle-run --run-id <run_id> --output projects/hard-sf-new-weird/bundles/")
    return rc


if __name__ == "__main__":
    sys.exit(main())

"""V12 Task 224e runner: clean seed-aligned rebuild + plan-only + review-plan for Ch1.

背景：224b 项目（hard-sf-new-weird-v12-224b-235415）的 Ch1-3 曾被 repair 脚本
强制通过 settlement 校验，证据链断裂。本脚本从 224b 克隆干净 seed（projects +
characters 行，不含任何 setting_tracking / foreshadowings / chapter 产物），
生成新 project_id，然后走完整 plan-only → review-plan → approve 流程。

Usage:
    python scripts/v12_224e_runner.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path

# 项目根
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

SPEC_PATH = ROOT / "projects" / "hard-sf-new-weird" / "planning" / "supervision_spec.json"
RUN_DIR = ROOT / "projects" / "hard-sf-new-weird" / "runs"
RUNTIME_DB = ROOT / "projects" / "hard-sf-new-weird" / "runtime" / "songyan.db"

SOURCE_PROJECT_ID = "hard-sf-new-weird-v12-224b-235415"

# 环境：DB + supervision spec（必须在 import songyan 之前设置）
os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
os.environ["CHECKPOINTER_MODE"] = "sqlite"
os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)

from songyan.services.plan_review import (  # noqa: E402
    approve_plan_review,
    review_plan_only_result,
    run_plan_only,
    save_approved_plan,
)
from songyan.services.supervision_spec import load_supervision_spec_file  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def gen_suffix() -> str:
    return time.strftime("%H%M%S", time.localtime())


def clone_seed(source_project_id: str, new_project_id: str) -> str:
    """从 224b 克隆 projects + characters 行到新 project_id，返回新 character_id。

    只复制 seed 行；setting_tracking / foreshadowings / chapter 产物一律不复制
    （它们指向被污染的 run 产物，不是 seed）。
    """
    con = sqlite3.connect(RUNTIME_DB)
    try:
        existing = con.execute(
            "SELECT 1 FROM projects WHERE project_id = ?", (new_project_id,)
        ).fetchone()
        if existing:
            raise RuntimeError(f"project already exists: {new_project_id}")

        proj_cols = [r[1] for r in con.execute("PRAGMA table_info(projects)")]
        row = con.execute(
            "SELECT * FROM projects WHERE project_id = ?", (source_project_id,)
        ).fetchone()
        if row is None:
            raise RuntimeError(f"source project not found: {source_project_id}")
        proj = dict(zip(proj_cols, row))
        proj["project_id"] = new_project_id
        proj["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        con.execute(
            f"INSERT INTO projects ({', '.join(proj_cols)}) VALUES ({', '.join('?' * len(proj_cols))})",
            [proj[c] for c in proj_cols],
        )

        char_cols = [r[1] for r in con.execute("PRAGMA table_info(characters)")]
        crows = con.execute(
            "SELECT * FROM characters WHERE project_id = ?", (source_project_id,)
        ).fetchall()
        if not crows:
            raise RuntimeError(f"source characters not found: {source_project_id}")
        new_character_id = f"char-{uuid.uuid4().hex[:8]}"
        for crow in crows:
            char = dict(zip(char_cols, crow))
            old_character_id = char["character_id"]
            char["character_id"] = new_character_id
            char["project_id"] = new_project_id
            if char.get("dialogue_style_card"):
                card = json.loads(char["dialogue_style_card"])
                if card.get("character_id") == old_character_id:
                    card["character_id"] = new_character_id
                card["project_id"] = new_project_id
                char["dialogue_style_card"] = json.dumps(card, ensure_ascii=False)
            char["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
            con.execute(
                f"INSERT INTO characters ({', '.join(char_cols)}) VALUES ({', '.join('?' * len(char_cols))})",
                [char[c] for c in char_cols],
            )
        con.commit()
        print(f"[224e] cloned seed: {source_project_id} -> {new_project_id}")
        print(f"[224e] new character_id: {new_character_id} (characters={len(crows)})")
        return new_character_id
    finally:
        con.close()


async def step_plan_only(project_id: str):
    print(f"\n[224e] === plan-only for Ch1 (project={project_id}) ===")
    result = await run_plan_only(project_id=project_id, chapters=[1])
    for art in result.artifacts:
        print(f"  - Ch{art.chapter_number}: goal={art.chapter_goal_id} brief={art.creative_brief_id}")
    return result


async def step_review(plan_result):
    print("\n[224e] === deterministic review-plan ===")
    spec = load_supervision_spec_file(SPEC_PATH)
    review = await review_plan_only_result(plan_result, spec)
    if review.findings:
        print(f"  REVIEW FAIL: {len(review.findings)} findings")
        for f in review.findings:
            print(f"    - Ch{f.chapter_number} [{f.code}] {f.message}")
            print(f"      evidence: {f.evidence}")
    else:
        print("  REVIEW PASS: 0 findings")
    return review


def step_save_artifacts(plan_result, review, stamp: str) -> Path | None:
    run_dir = RUN_DIR / f"v12_task224e_ch1_plan_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    plan_path = run_dir / "plan_only_result.json"
    plan_path.write_text(
        json.dumps(plan_result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  plan-only saved: {plan_path}")

    review_path = run_dir / "plan_review_result.json"
    review_path.write_text(
        json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  review-plan saved: {review_path}")

    if not review.passed:
        return None

    approval = approve_plan_review(review)
    approval_path = run_dir / "approved_plan_ch1.json"
    save_approved_plan(approval_path, approval)
    print(f"  approved-plan saved: {approval_path}")
    return approval_path


async def main() -> int:
    stamp = gen_suffix()
    project_id = f"hard-sf-new-weird-v12-224e-{stamp}"

    print(f"[224e] V12 Task 224e clean rebuild + Ch1-only closure - started at {stamp}")
    print(f"[224e] source seed project: {SOURCE_PROJECT_ID}")
    print(f"[224e] new project_id     : {project_id}")
    print(f"[224e] supervision spec   : {SPEC_PATH}")

    clone_seed(SOURCE_PROJECT_ID, project_id)

    plan_result = await step_plan_only(project_id)
    review = await step_review(plan_result)
    approval_path = step_save_artifacts(plan_result, review, stamp)

    if not review.passed:
        print("\n[224e] STOP: review-plan rejected. Report findings to user; do NOT auto-retry.")
        return 2

    print("\n" + "=" * 60)
    print("[224e] Plan review PASSED. Now run REAL SMOKE with:")
    print("=" * 60)
    print(f"""
$env:DATABASE_URL = "sqlite:///{RUNTIME_DB.as_posix()}"
$env:CHECKPOINTER_MODE = "sqlite"
$env:SONGYAN_STARTUP_SUPERVISION_SPEC = "{SPEC_PATH}"
$env:SONGYAN_STARTUP_APPROVED_PLAN = "{approval_path}"

powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 3600 -- `
  songyan run --project-id {project_id} --chapters 1 --auto-confirm --on-failure isolate
""")
    print("After run completes:")
    print(f"""
songyan report --project-id {project_id} --last-run
songyan export --project-id {project_id} --chapters 1 --format md --output projects/hard-sf-new-weird/exports/ch001_round_v12_224e/
songyan bundle-run --run-id <run_id> --output projects/hard-sf-new-weird/bundles/
""")
    return 0


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)

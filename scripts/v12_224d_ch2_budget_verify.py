"""V12-224d Ch2 context budget verification (non-destructive).

Assembles Ch2's ContextPackage with the NEW profile (base_budget=9500,
ramp_per_chapter=300) and reports budget_used / context_emergency without
going through the full pipeline (which would skip Ch2 since it's accepted).

This directly tests whether the ContextEmergency fix is effective, without
LLM calls and without touching the accepted_version_id.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

DB = ROOT / "projects" / "hard-sf-new-weird" / "runtime" / "songyan.db"
PROJECT_ID = "hard-sf-new-weird-v12-224b-235415"
CHAPTER_NUMBER = 2
SPEC_PATH = ROOT / "projects" / "hard-sf-new-weird" / "planning" / "supervision_spec.json"
APPROVED_PLAN_DIRS = sorted(
    (ROOT / "projects" / "hard-sf-new-weird" / "runs").glob(
        "v12_task224d_ch2_plan_*/approved_plan_ch2.json"
    )
)
APPROVED_PLAN_PATH = APPROVED_PLAN_DIRS[-1] if APPROVED_PLAN_DIRS else None


async def main() -> int:
    os.environ["DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
    os.environ["CHECKPOINTER_MODE"] = "sqlite"
    os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)
    if APPROVED_PLAN_PATH:
        os.environ["SONGYAN_STARTUP_APPROVED_PLAN"] = str(APPROVED_PLAN_PATH)

    from songyan.db import ChapterGoalRepository, CreativeBriefRepository
    from songyan.workflows._helpers import assemble_context_package
    from songyan.db.genre_runtime_profile_repo import load_profile

    # Load approved-plan-locked goal + brief (same as pipeline would)
    goal_repo = ChapterGoalRepository()
    brief_repo = CreativeBriefRepository()

    # Query goal_id and brief_id from DB for logging (models don't carry them)
    import sqlite3
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT goal_id FROM chapter_goals WHERE project_id=? AND chapter_number=? ORDER BY datetime(created_at) DESC LIMIT 1",
        (PROJECT_ID, CHAPTER_NUMBER),
    )
    goal_row = cur.fetchone()
    cur = conn.execute(
        "SELECT brief_id FROM creative_briefs WHERE project_id=? AND chapter_number=? ORDER BY datetime(created_at) DESC LIMIT 1",
        (PROJECT_ID, CHAPTER_NUMBER),
    )
    brief_row = cur.fetchone()
    conn.close()

    ch2_goal = await goal_repo.get_by_chapter(PROJECT_ID, CHAPTER_NUMBER)
    if ch2_goal is None:
        print(f"ERROR: no ChapterGoal found for Ch{CHAPTER_NUMBER}")
        return 2

    ch2_brief = None
    if brief_row:
        ch2_brief = await brief_repo.get(brief_row["brief_id"])

    print(f"=== Ch{CHAPTER_NUMBER} context budget verification ===")
    print(f"project_id        : {PROJECT_ID}")
    print(f"goal_id           : {goal_row['goal_id'] if goal_row else None}")
    print(f"brief_id          : {brief_row['brief_id'] if brief_row else None}")
    print(f"approved_plan     : {APPROVED_PLAN_PATH}")

    # Verify effective profile
    profile = await load_profile("scifi")
    expected_budget = profile.base_budget + CHAPTER_NUMBER * profile.ramp_per_chapter
    print(f"\n=== effective profile (scifi) ===")
    print(f"base_budget       : {profile.base_budget}  (expected 9500)")
    print(f"ramp_per_chapter  : {profile.ramp_per_chapter}  (expected 300)")
    print(f"min_budget        : {profile.min_budget}")
    print(f"expected Ch{CHAPTER_NUMBER} budget : {expected_budget}  (old was 8500)")

    # Assemble context (this is what context_manager_node does internally)
    print(f"\n=== assembling ContextPackage (no LLM calls) ===")
    ctx = await assemble_context_package(
        project_id=PROJECT_ID,
        chapter_number=CHAPTER_NUMBER,
        chapter_goal=ch2_goal,
        creative_brief=ch2_brief,
        narrative_fullness=ch2_brief.narrative_fullness if ch2_brief else 0.0,
        character_focus=ch2_brief.character_focus if ch2_brief else None,
        foreshadowing_due=ch2_brief.foreshadowing_due if ch2_brief else None,
        focal_distance=ch2_brief.focal_distance if ch2_brief else "mid",
    )

    print(f"\n=== RESULT ===")
    print(f"estimated_tokens           : {ctx.estimated_tokens}")
    print(f"budget_used                : {round(ctx.budget_used, 4)}")
    print(f"context_emergency          : {ctx.context_emergency}")
    print(f"context_emergency_level    : {ctx.context_emergency_level}")
    print(f"budget_used_before_emergency: {ctx.budget_used_before_emergency}")
    print(f"budget_enforced            : {getattr(ctx, '_budget_enforced', False)}")

    if ctx.context_pressure:
        print(f"\n=== context_pressure ===")
        for k, v in ctx.context_pressure.items():
            print(f"  {k}: {v}")

    print(f"\n=== partition sizes (counts) ===")
    print(f"  hard_constraints  : {len(ctx.hard_constraints) if ctx.hard_constraints else 0}")
    print(f"  character_states  : {len(ctx.character_states) if ctx.character_states else 0}")
    print(f"  foreshadowing     : {len(ctx.foreshadowing) if ctx.foreshadowing else 0}")
    print(f"  soft_references   : {len(ctx.soft_references) if ctx.soft_references else 0}")
    print(f"  open_threads      : {len(ctx.open_threads) if ctx.open_threads else 0}")
    print(f"  permanent_scenes  : {len(ctx.permanent_scenes) if ctx.permanent_scenes else 0}")
    print(f"  human_marks       : {len(ctx.human_marks) if ctx.human_marks else 0}")
    print(f"  dialogue_style_cards: {len(ctx.dialogue_style_cards) if ctx.dialogue_style_cards else 0}")

    # Verdict
    print(f"\n=== VERDICT ===")
    if not ctx.context_emergency and ctx.budget_used <= 1.0:
        print(f"PASS: ContextEmergency NOT triggered, budget_used={round(ctx.budget_used, 4)} <= 1.0")
        print(f"  Fix effective: {ctx.estimated_tokens}/{expected_budget} tokens ({round(ctx.budget_used*100, 1)}%)")
        return 0
    elif ctx.context_emergency:
        print(f"FAIL: ContextEmergency STILL triggered")
        print(f"  before_emergency={ctx.budget_used_before_emergency}, after={ctx.budget_used}")
        print(f"  Recommendation: bump base_budget further (e.g., 10500)")
        return 1
    else:
        print(f"WARN: budget_used={round(ctx.budget_used, 4)} > 1.0 but no emergency (edge case)")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

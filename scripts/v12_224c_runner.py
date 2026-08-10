"""V12 Task 224c runner: plan-only + review-plan for hard-sf-new-weird Ch1.

Usage:
    python scripts/v12_224c_runner.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# 项目根
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

SPEC_PATH = ROOT / "projects" / "hard-sf-new-weird" / "planning" / "supervision_spec.json"
RUN_DIR = ROOT / "projects" / "hard-sf-new-weird" / "runs"
RUNTIME_DB = ROOT / "projects" / "hard-sf-new-weird" / "runtime" / "songyan.db"

# 环境：DB + supervision spec
os.environ.setdefault("DATABASE_URL", f"sqlite:///{RUNTIME_DB.as_posix()}")
os.environ.setdefault("CHECKPOINTER_MODE", "sqlite")
os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)


from songyan.db.repository import ProjectRepository  # noqa: E402
from songyan.project_templates.loader import ProjectTemplateLoader  # noqa: E402
from songyan.project_templates.initializer import ProjectInitializer  # noqa: E402
from songyan.services.plan_review import (  # noqa: E402
    approve_plan_review,
    review_plan_only_result,
    run_plan_only,
    save_approved_plan,
)
from songyan.services.supervision_spec import load_supervision_spec_file  # noqa: E402


def gen_suffix() -> str:
    now = time.localtime()
    return time.strftime("%H%M%S", now)


async def create_clean_project(stamp: str) -> str:
    """从内置 scifi 模板创建干净项目。"""
    template = ProjectTemplateLoader().load("scifi")
    # 修改模板项
    if hasattr(template, "project_setting"):
        try:
            template.project_setting.project_name = "静默协议"
        except Exception:
            pass
    project_id, _ = await ProjectInitializer.from_template(template)
    print(f"[224c] created clean project {project_id} (stamp={stamp})")
    return project_id


async def step1_plan_only(project_id: str) -> object:
    print(f"\n[224c] === Step 1: plan-only for Ch1 (project={project_id}) ===")
    result = await run_plan_only(project_id=project_id, chapters=[1])
    for art in result.artifacts:
        print(f"  - Ch{art.chapter_number}: goal={art.chapter_goal_id} brief={art.creative_brief_id}")
    return result


async def step2_review_plan(plan_result: object) -> object:
    print("\n[224c] === Step 2: deterministic review-plan ===")
    spec = load_supervision_spec_file(SPEC_PATH)
    review = await review_plan_only_result(plan_result, spec)
    if review.findings:
        print(f"  ❌ REVIEW FAIL: {len(review.findings)} findings")
        for f in review.findings:
            print(f"    - Ch{f.chapter_number} [{f.code}] {f.message}")
            print(f"      evidence: {f.evidence}")
    else:
        print("  ✅ REVIEW PASS: 0 findings")
    return review


def step3_save_artifacts(project_id: str, plan_result: object, review: object, stamp: str) -> tuple[Path | None, Path | None]:
    run_dir = RUN_DIR / f"v12_task224c_ch1_plan_{stamp}"
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
        return plan_path, review_path

    approval = approve_plan_review(review)
    approval_path = run_dir / "approved_plan_ch1.json"
    save_approved_plan(approval_path, approval)
    print(f"  ✅ approved-plan saved: {approval_path}")
    return plan_path, approval_path


async def main() -> int:
    stamp = gen_suffix()
    # 复用 224b 已经 seed-aligned 的 project（主角=沈砚，标题=静默协议）
    project_id = "hard-sf-new-weird-v12-224b-235415"

    print(f"[224c] V12 Task 224c Ch1-only closure - started at {stamp}")
    print(f"[224c] reuse seed-aligned project: {project_id}")
    print(f"[224c] supervision spec: {SPEC_PATH}")

    # Step 1-2: plan-only + review-plan
    plan_result = await step1_plan_only(project_id)
    review = await step2_review_plan(plan_result)

    # Step 3: save artifacts
    plan_path, approval_or_review = step3_save_artifacts(project_id, plan_result, review, stamp)

    if not review.passed:
        print("\n[224c] STOP: review-plan rejected. Adjust supervision spec / plan and retry.")
        return 2

    # Output real-run instruction
    print("\n" + "=" * 60)
    print("[224c] Plan review PASSED. Now run REAL SMOKE with:")
    print("=" * 60)
    approval_path = approval_or_review
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
songyan report --run-id <run_id>
songyan export --project-id {project_id} --chapters 1 --format md --output projects/hard-sf-new-weird/exports/ch001_round_v12_224c/
songyan bundle-run --run-id <run_id> --output projects/hard-sf-new-weird/bundles/
""")
    return 0


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)

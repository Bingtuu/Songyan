"""真实 LLM 多章验证脚本 — 验证 Task 023 跨章状态传递.

用法:
    python scripts/run_real_llm_multi_chapter.py [--seed xuanhuan|scifi|urban]

验证点:
    1. Chapter 2 的 previous_summary 包含 Chapter 1 剧情
    2. Chapter 3 的 previous_summary 包含 Chapter 2 剧情
    3. 多章 Pipeline 稳定完成
    4. project_runs 表正确记录进度
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from sqlite3 import Row
from typing import Any
from unittest.mock import patch

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.llm.client import call_llm
from songyan.workflows.phase1_graph import reset_checkpointer
from songyan.workflows.phase2_graph import run_project_pipeline

# evals imports
from evals.runner import import_seed_chapter, import_seed_project


# =============================================================================
# LLM 调用包装器
# =============================================================================

LLM_CALLS: list[dict[str, Any]] = []


async def _wrapped_call_llm(
    prompt: str,
    *,
    temperature: float = 0.7,
    max_retries: int = 3,
    _agent_name: str = "unknown",
) -> str:
    t0 = time.perf_counter()
    try:
        response = await call_llm(prompt=prompt, temperature=temperature, max_retries=max_retries)
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        LLM_CALLS.append(
            {
                "agent": _agent_name,
                "timestamp": datetime.now().isoformat(),
                "elapsed_ms": elapsed_ms,
                "prompt_chars": len(prompt),
                "response_chars": 0,
                "error": str(exc),
                "temperature": temperature,
            }
        )
        raise

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    LLM_CALLS.append(
        {
            "agent": _agent_name,
            "timestamp": datetime.now().isoformat(),
            "elapsed_ms": elapsed_ms,
            "prompt_chars": len(prompt),
            "response_chars": len(response),
            "temperature": temperature,
        }
    )
    return response


# =============================================================================
# Main
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python scripts/run_real_llm_multi_chapter.py")
    parser.add_argument(
        "--seed",
        default="xuanhuan",
        choices=["xuanhuan", "scifi", "urban"],
        help="种子项目类型",
    )
    parser.add_argument(
        "--chapters",
        type=int,
        default=2,
        help="生成章节数（从第2章开始）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="验证 API Key 和配置后退出",
    )
    return parser


async def _main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print("=" * 60)
    print("Songyan 真实 LLM 多章验证 -- Task 023")
    print("=" * 60)

    if not settings.llm_api_key:
        print("\n[ERROR] LLM_API_KEY 未配置")
        return 1

    print(f"\n[OK] API Key 已配置 (model={settings.llm_model})")

    if args.dry_run:
        print("\n🧪 --dry-run 模式：只验证配置，不调用 LLM")
        try:
            from songyan.llm.client import get_llm

            get_llm()
            print("   LLM 初始化验证通过")
        except Exception as exc:
            print(f"   LLM 初始化失败: {exc}")
            return 1
        return 0

    # 种子配置映射
    seed_configs = {
        "xuanhuan": ("evals/seeds/xuanhuan_webnovel.json", "evals/seeds/chapters/xuanhuan_ch1.md"),
        "scifi": ("evals/seeds/scifi_new_weird.json", "evals/seeds/chapters/scifi_new_weird_ch1.md"),
        "urban": ("evals/seeds/urban_hybrid.json", "evals/seeds/chapters/urban_ch1.md"),
    }
    seed_config_path, seed_chapter_path = seed_configs[args.seed]

    # 准备环境
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"evals/output/multi_chapter_{args.seed}_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = output_dir / "test.db"
    settings.database_url = f"sqlite:///{db_path}"
    print(f"\n📁 输出目录: {output_dir.resolve()}")
    print(f"🗄️  临时数据库: {db_path}")

    await init_schema()
    print("   数据库 schema 初始化完成")

    # Patch call_llm
    targets = [
        ("songyan.agents.goal_planner.call_llm", "goal_planner"),
        ("songyan.agents.creative_director.call_llm", "creative_director"),
        ("songyan.agents.writer.call_llm", "writer"),
        ("songyan.agents.llm_auditor.call_llm", "llm_auditor"),
        ("songyan.agents.literary_auditor.call_llm", "literary_auditor"),
        ("songyan.agents.revision_handler.call_llm", "revision_handler"),
        ("songyan.agents.settlement_extractor.call_llm", "settlement_extractor"),
        ("songyan.agents.summary_writer.call_llm", "summary_writer"),
    ]

    def _make_wrapper(agent_name: str):
        async def wrapper(prompt: str = "", *, temperature: float = 0.7, max_retries: int = 3, **kwargs: Any) -> str:
            return await _wrapped_call_llm(
                prompt, temperature=temperature, max_retries=max_retries, _agent_name=agent_name
            )

        return wrapper

    print(f"\n🎯 开始多章验证（生成 Ch2 → Ch{1 + args.chapters}）")
    print(f"   预估调用 ~{args.chapters * 7} 次 LLM，成本约 ¥{args.chapters * 0.11:.2f}")
    print("   按 Ctrl+C 可随时中断\n")

    await reset_checkpointer()
    LLM_CALLS.clear()

    total_start = time.perf_counter()

    with contextlib.ExitStack() as stack:
        for target, agent_name in targets:
            stack.enter_context(patch(target, _make_wrapper(agent_name)))

        try:
            # 1. 导入种子项目
            print("📥 导入种子项目...")
            project_id = await import_seed_project(seed_config_path)
            print(f"   项目 ID: {project_id}")

            # 2. 导入种子章节（作为 Chapter 1）
            print("📥 导入种子章节（Chapter 1）...")
            await import_seed_chapter(project_id, seed_chapter_path, chapter_number=1)
            print("   完成")

            # 3. 运行多章流水线
            print("\n🚀 启动多章流水线...")
            result = await run_project_pipeline(
                project_id=project_id,
                chapter_range=(2, 1 + args.chapters),
                mode_id="webnovel",
                auto_confirm=True,
                on_failure="abort",
            )
        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断")
            return 130
        except Exception as exc:
            print(f"\n❌ 运行失败: {exc}")
            import traceback

            traceback.print_exc()
            return 1

    total_elapsed_ms = int((time.perf_counter() - total_start) * 1000)

    # ------------------------------------------------------------------
    # 验证结果
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)

    print(f"\n📊 ProjectRunResult:")
    print(f"   项目 ID: {result.project_id}")
    print(f"   Run ID: {result.run_id}")
    print(f"   完成章节: {result.chapters_completed}")
    print(f"   失败章节: {result.chapters_failed}")
    print(f"   最终状态: {result.final_status}")
    print(f"   总耗时: {result.total_duration_sec:.1f}s")

    # 验证 1: project_runs 表
    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            "SELECT * FROM project_runs WHERE run_id = ?",
            (result.run_id,),
        )
        run_row = await cursor.fetchone()

    if run_row:
        print(f"\n✅ project_runs 表记录存在")
        print(f"   status: {run_row['status']}")
        print(f"   completed: {run_row['completed_chapters']}")
    else:
        print(f"\n❌ project_runs 表记录不存在")

    # 验证 2: summaries 表
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT chapter_number, plot_summary FROM summaries WHERE project_id = ? ORDER BY chapter_number",
            (project_id,),
        )
        summary_rows = await cursor.fetchall()

    print(f"\n📋 summaries 表记录（{len(summary_rows)} 条）:")
    for row in summary_rows:
        print(f"   Ch{row[0]}: {row[1][:60]}...")

    # 验证 3: chapter_goals 的 previous_summary
    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            "SELECT chapter_number, previous_summary FROM chapter_goals WHERE project_id = ? ORDER BY chapter_number",
            (project_id,),
        )
        goal_rows = await cursor.fetchall()

    print(f"\n🎯 chapter_goals previous_summary 验证:")
    prev_summaries: dict[int, str] = {}
    for row in goal_rows:
        ch = row["chapter_number"]
        ps = row["previous_summary"] or ""
        prev_summaries[ch] = ps
        print(f"   Ch{ch}: len={len(ps)}  {'✅ 非空' if ps else '❌ 空'}")

    # 验证 4: 跨章连贯性（Ch2 的 previous_summary 应包含 Ch1 的内容）
    ch1_summary = next((r[1] for r in summary_rows if r[0] == 1), "")
    ch2_prev = prev_summaries.get(2, "")
    ch2_summary = next((r[1] for r in summary_rows if r[0] == 2), "")
    ch3_prev = prev_summaries.get(3, "")

    print(f"\n🔗 跨章连贯性验证:")
    if ch1_summary and ch2_prev:
        # 简单验证：Ch2 的 previous_summary 和 Ch1 的 summary 有重叠
        overlap = len(set(ch2_prev.split()) & set(ch1_summary.split()))
        print(f"   Ch2 previous_summary 与 Ch1 summary 重叠词数: {overlap}")
        print(f"   {'✅ 跨章传递生效' if overlap > 0 else '⚠️ 重叠度低'}")
    else:
        print(f"   ⚠️ 数据不足，无法验证")

    if ch2_summary and ch3_prev:
        overlap = len(set(ch3_prev.split()) & set(ch2_summary.split()))
        print(f"   Ch3 previous_summary 与 Ch2 summary 重叠词数: {overlap}")
        print(f"   {'✅ 跨章传递生效' if overlap > 0 else '⚠️ 重叠度低'}")

    # ------------------------------------------------------------------
    # LLM 调用统计
    # ------------------------------------------------------------------
    print(f"\n📞 LLM 调用统计（共 {len(LLM_CALLS)} 次）:")
    for call in LLM_CALLS:
        status = "❌" if "error" in call else "✅"
        print(
            f"   {status} {call['agent']:20s}  {call['elapsed_ms']:5d}ms  "
            f"prompt={call['prompt_chars']:5d}  response={call['response_chars']:5d}"
        )

    from songyan.utils.cost_estimator import estimate_cost_from_calls, format_cost_estimate

    est_cost_cny = estimate_cost_from_calls(LLM_CALLS)
    print(f"\n💰 预估成本: {format_cost_estimate(est_cost_cny)}")

    # ------------------------------------------------------------------
    # 保存输出
    # ------------------------------------------------------------------
    llm_log_path = output_dir / "llm_calls.jsonl"
    with llm_log_path.open("w", encoding="utf-8") as f:
        for call in LLM_CALLS:
            f.write(json.dumps(call, ensure_ascii=False) + "\n")

    summary_data = {
        "project_id": project_id,
        "run_id": result.run_id,
        "seed": args.seed,
        "chapters_completed": result.chapters_completed,
        "chapters_failed": result.chapters_failed,
        "final_status": result.final_status,
        "duration_sec": result.total_duration_sec,
        "total_elapsed_ms": total_elapsed_ms,
        "llm_call_count": len(LLM_CALLS),
        "estimated_cost_cny": est_cost_cny,
        "summaries": [{"chapter": r[0], "summary": r[1]} for r in summary_rows],
        "previous_summaries": {str(k): v for k, v in prev_summaries.items()},
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n📁 所有输出已保存至: {output_dir.resolve()}")

    if result.final_status == "completed" and not result.chapters_failed:
        print("\n🎉 多章验证通过！")
        return 0
    else:
        print("\n⚠️  多章验证未通过")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(_main()))
    except KeyboardInterrupt:
        print("\n已取消。")
        sys.exit(130)

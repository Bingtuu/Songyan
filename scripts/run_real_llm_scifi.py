"""真实 LLM 单章评测脚本 — 科幻新怪谈种子项目.

用法:
    python scripts/run_real_llm_scifi.py [--dry-run]
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
from typing import Any
from unittest.mock import patch

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.repository import ChapterVersionRepository
from songyan.db.review_repo import ReviewReportRepository
from songyan.llm.client import call_llm
from songyan.models import (
    ChapterVersion,
    CharacterUpdate,
    MergedReviewReport,
    NewSetting,
    NumericalUpdate,
    StateSettlement,
)

# evals imports
from evals.metrics import MetricsCollector
from evals.runner import run_seed_project
from evals.models import EvaluationResult
from songyan.workflows.phase1_graph import reset_checkpointer


# =============================================================================
# LLM 调用包装器（记录日志 + 统计）
# =============================================================================

LLM_CALLS: list[dict[str, Any]] = []


async def _wrapped_call_llm(
    prompt: str,
    *,
    temperature: float = 0.7,
    max_retries: int = 3,
    _agent_name: str = "unknown",
) -> str:
    """包装原始 call_llm，记录耗时和 token 估算."""
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
    parser = argparse.ArgumentParser(prog="python scripts/run_real_llm_scifi.py")
    parser.add_argument("--dry-run", action="store_true", help="验证 API Key 和配置后退出")
    parser.add_argument(
        "--seed-config",
        default="evals/seeds/scifi_new_weird.json",
        help="种子项目配置 JSON 路径",
    )
    parser.add_argument(
        "--seed-chapter",
        default="evals/seeds/chapters/scifi_new_weird_ch1.md",
        help="种子章节 Markdown 路径",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="输出目录（默认自动生成）",
    )
    return parser


async def _main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # 0. 前置检查
    # ------------------------------------------------------------------
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print("=" * 60)
    print("Songyan 真实 LLM 单章评测 -- 科幻新怪谈")
    print("=" * 60)

    if not settings.llm_api_key:
        print("\n[ERROR] LLM_API_KEY 未配置")
        print("   请检查 .env 文件或环境变量。")
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

    # ------------------------------------------------------------------
    # 1. 准备隔离环境
    # ------------------------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else Path(f"evals/output/real_llm_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 临时 DB（覆盖 database_url）
    db_path = output_dir / "test.db"
    settings.database_url = f"sqlite:///{db_path}"
    print(f"\n📁 输出目录: {output_dir.resolve()}")
    print(f"🗄️  临时数据库: {db_path}")

    await init_schema()
    print("   数据库 schema 初始化完成")

    # ------------------------------------------------------------------
    # 2. Patch call_llm（全局包装）
    # ------------------------------------------------------------------
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

    print("\n🎯 开始运行评测（单章闭环: Ch1 → Ch2）")
    print("   预估调用 7 次 LLM，成本约 ¥0.5 ~ ¥3")
    print("   按 Ctrl+C 可随时中断\n")

    await reset_checkpointer()
    LLM_CALLS.clear()

    # ------------------------------------------------------------------
    # 3. 运行评测
    # ------------------------------------------------------------------
    total_start = time.perf_counter()

    with contextlib.ExitStack() as stack:
        for target, agent_name in targets:
            stack.enter_context(patch(target, _make_wrapper(agent_name)))

        try:
            result: EvaluationResult = await run_seed_project(
                project_config_path=args.seed_config,
                seed_chapter_path=args.seed_chapter,
                output_dir=str(output_dir),
                auto_accept=True,
            )
        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断")
            return 130
        except Exception as exc:
            print(f"\n❌ 评测运行失败: {exc}")
            import traceback

            traceback.print_exc()
            return 1

    total_elapsed_ms = int((time.perf_counter() - total_start) * 1000)

    # ------------------------------------------------------------------
    # 4. 收集 MetricsCollector
    # ------------------------------------------------------------------
    print("\n📊 收集验收指标...")

    version: ChapterVersion | None = None
    report: MergedReviewReport | None = None
    settlement = StateSettlement()

    if result.chapter_version_id:
        version = await ChapterVersionRepository().get(result.chapter_version_id)
    if result.merged_review_report_id:
        report = await ReviewReportRepository().get_by_version(result.chapter_version_id)

    # settlement 需要从 DB 重建（run_seed_project 已应用）
    settlement = StateSettlement()
    if result.settlement_id and result.chapter_version_id:
        async with get_db() as conn:
            # character_updates
            cursor = await conn.execute(
                "SELECT character_id, field, value FROM character_states WHERE source_version_id = ?",
                (result.chapter_version_id,),
            )
            rows = await cursor.fetchall()
            character_updates = [
                CharacterUpdate(
                    character_id=r[0],
                    field=r[1],
                    old_value="",
                    new_value=r[2],
                    source_quote="",
                )
                for r in rows
            ]

            # new_settings
            cursor = await conn.execute(
                "SELECT setting_name, description, source_quote, setting_key FROM setting_snapshots WHERE project_id = ?",
                (result.project_id,),
            )
            rows = await cursor.fetchall()
            new_settings = [
                NewSetting(
                    setting_name=r[0],
                    description=r[1] or "",
                    source_quote=r[2] or "",
                    setting_key=r[3] or "",
                )
                for r in rows
            ]

            # numerical_updates
            cursor = await conn.execute(
                "SELECT character_id, attribute_name, opening_value, closing_value FROM numerical_ledgers WHERE project_id = ? AND chapter_number = ?",
                (result.project_id, version.chapter_number if version else 2),
            )
            rows = await cursor.fetchall()
            numerical_updates = [
                NumericalUpdate(
                    character_id=r[0],
                    attribute_name=r[1],
                    opening_value=r[2] or 0.0,
                    closing_value=r[3] or 0.0,
                )
                for r in rows
            ]

        settlement = StateSettlement(
            character_updates=character_updates,
            new_settings=new_settings,
            numerical_updates=numerical_updates,
        )

    mc = MetricsCollector(
        version=version or ChapterVersion(version_id="", project_id="", chapter_number=2),
        review_report=report or MergedReviewReport(chapter_version_id=""),
        settlement=settlement,
        duration_ms=result.duration_ms,
    )
    metrics = await mc.collect_async()
    is_pass = await mc.is_pass()

    # ------------------------------------------------------------------
    # 5. 持久化附加输出
    # ------------------------------------------------------------------
    # LLM 调用日志
    llm_log_path = output_dir / "llm_calls.jsonl"
    with llm_log_path.open("w", encoding="utf-8") as f:
        for call in LLM_CALLS:
            f.write(json.dumps(call, ensure_ascii=False) + "\n")

    # metrics.json
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # summary.txt（人类可读）
    summary_lines = [
        "=" * 60,
        "Songyan 真实 LLM 单章评测报告",
        "=" * 60,
        "",
        f"项目: {result.project_name}",
        f"题材: {result.genre_id} / 模式: {result.mode_id}",
        f"种子配置: {args.seed_config}",
        f"",
        f"运行时间: {result.duration_ms}ms ({result.duration_ms / 1000:.1f}s)",
        f"总耗时(含脚本): {total_elapsed_ms}ms",
        f"输出目录: {output_dir}",
        f"",
        "--- LLM 调用统计 ---",
    ]

    for call in LLM_CALLS:
        summary_lines.append(
            f"  {call['agent']:20s}  {call['elapsed_ms']:5d}ms  "
            f"prompt={call['prompt_chars']:5d}  response={call['response_chars']:5d}"
        )

    total_prompt = sum(c["prompt_chars"] for c in LLM_CALLS)
    total_response = sum(c["response_chars"] for c in LLM_CALLS)
    summary_lines.append(f"  {'TOTAL':20s}  {'':5s}  prompt={total_prompt:5d}  response={total_response:5d}")

    # 成本估算（基于 tiktoken 精确计算）
    from songyan.utils.cost_estimator import estimate_cost_from_calls, format_cost_estimate

    est_cost_cny = estimate_cost_from_calls(LLM_CALLS)
    summary_lines.append(f"  预估成本: {format_cost_estimate(est_cost_cny)}")

    summary_lines.extend([
        "",
        "--- 验收指标 ---",
    ])
    for k, v in metrics.items():
        summary_lines.append(f"  {k:30s}: {v}")

    summary_lines.extend([
        "",
        f"--- 验收结果 ---",
        f"  is_pass: {'✅ 通过' if is_pass else '❌ 未通过'}",
        "",
        "=" * 60,
    ])

    summary_txt = "\n".join(summary_lines)
    (output_dir / "summary.txt").write_text(summary_txt, encoding="utf-8")

    # ------------------------------------------------------------------
    # 6. 打印到终端
    # ------------------------------------------------------------------
    print(summary_txt)

    if is_pass:
        print("\n🎉 评测通过！所有可计算指标均达标。")
    else:
        print("\n⚠️  评测未通过。请查看 metrics.json 了解具体未达标项。")

    print(f"\n📁 所有输出已保存至: {output_dir.resolve()}")
    return 0 if result.success else 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(_main()))
    except KeyboardInterrupt:
        print("\n已取消。")
        sys.exit(130)

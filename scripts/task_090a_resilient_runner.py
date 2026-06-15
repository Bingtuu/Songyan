#!/usr/bin/env python3
"""Task 090a: Phase B Ch1-Ch20 端到端回流验证 — Resilient Runner.

核心设计原则:
- 断点续跑: progress.json 保存状态, 重启自动恢复
- 失败不阻塞: 单章失败后记录并继续下一章
- 详细 metrics: 每章收集字数/budget/revision/耗时/错误
- 实时监控: 打印进度、预估剩余时间

用法:
    python scripts/task_090a_resilient_runner.py [--resume-dir DIR] [--chapters 20]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import signal
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Row
from typing import Any
from unittest.mock import patch

# Windows 控制台 UTF-8 编码修复
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 确保项目根目录在 sys.path 中（支持从任意目录运行脚本）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.llm.client import call_llm
from songyan.workflows.phase1_graph import reset_checkpointer
from songyan.workflows.phase2_graph import run_project_pipeline
from evals.runner import import_seed_chapter, import_seed_project
from songyan.utils.cost_estimator import estimate_cost_from_calls, format_cost_estimate

# ---------------------------------------------------------------------------
# 常量配置
# ---------------------------------------------------------------------------
SEED_CONFIG_PATH = "evals/seeds/scifi_webnovel.json"
SEED_CHAPTER_PATH = "evals/seeds/chapters/scifi_ch1.md"
DEFAULT_MODE_ID = "webnovel"
DEFAULT_START_CHAPTER = 2
DEFAULT_END_CHAPTER = 20
DEFAULT_OUTPUT_DIR = Path("evals/output/task_090a_scifi_webnovel")
DEFAULT_MD_DIR = Path("projects/task_090a_scifi_novel/chapters")

# ---------------------------------------------------------------------------
# LLM 调用追踪
# ---------------------------------------------------------------------------
LLM_CALLS: list[dict[str, Any]] = []


async def _wrapped_call_llm(
    prompt: str = "",
    *,
    temperature: float = 0.7,
    max_retries: int = 3,
    _agent_name: str = "unknown",
    **kwargs: Any,
) -> str:
    t0 = time.perf_counter()
    try:
        response = await call_llm(prompt=prompt, temperature=temperature, max_retries=max_retries)
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        LLM_CALLS.append(
            {
                "agent": _agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": elapsed_ms,
            "prompt_chars": len(prompt),
            "response_chars": len(response),
            "temperature": temperature,
        }
    )
    return response


def _make_wrapper(agent_name: str):
    async def wrapper(
        prompt: str = "", *, temperature: float = 0.7, max_retries: int = 3, **kwargs: Any
    ) -> str:
        return await _wrapped_call_llm(
            prompt, temperature=temperature, max_retries=max_retries, _agent_name=agent_name
        )

    return wrapper


# ---------------------------------------------------------------------------
# Progress 管理
# ---------------------------------------------------------------------------
class ProgressState:
    def __init__(self, data: dict | None = None):
        self.data = data or {}

    @property
    def project_id(self) -> str | None:
        return self.data.get("project_id")

    @project_id.setter
    def project_id(self, value: str):
        self.data["project_id"] = value

    @property
    def completed_chapters(self) -> list[int]:
        return self.data.get("completed_chapters", [])

    @property
    def failed_chapters(self) -> list[dict]:
        return self.data.get("failed_chapters", [])

    @property
    def skipped_chapters(self) -> list[int]:
        return self.data.get("skipped_chapters", [])

    @property
    def chapter_metrics(self) -> dict[str, dict]:
        return self.data.get("chapter_metrics", {})

    def mark_completed(self, chapter: int, metrics: dict):
        if chapter not in self.completed_chapters:
            self.data.setdefault("completed_chapters", []).append(chapter)
        self.data.setdefault("chapter_metrics", {})[str(chapter)] = metrics

    def mark_failed(self, chapter: int, error: str, attempts: int = 1):
        existing = next((f for f in self.failed_chapters if f["chapter"] == chapter), None)
        if existing:
            existing["attempts"] = attempts
            existing["last_error"] = error
            existing["timestamp"] = datetime.now(timezone.utc).isoformat()
        else:
            self.data.setdefault("failed_chapters", []).append(
                {
                    "chapter": chapter,
                    "attempts": attempts,
                    "last_error": error,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    def mark_skipped(self, chapter: int):
        if chapter not in self.skipped_chapters:
            self.data.setdefault("skipped_chapters", []).append(chapter)

    def is_done(self, chapter: int) -> bool:
        return chapter in self.completed_chapters or chapter in self.skipped_chapters

    def to_dict(self) -> dict:
        return self.data

    @classmethod
    def load(cls, path: Path) -> "ProgressState":
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return cls(json.load(f))
        return cls()

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Metrics 收集
# ---------------------------------------------------------------------------
async def _collect_chapter_metrics(
    project_id: str, chapter_number: int, db_path: Path
) -> dict[str, Any]:
    """从数据库收集单章 metrics."""
    metrics: dict[str, Any] = {"chapter": chapter_number}

    async with get_db() as conn:
        conn.row_factory = Row

        # 1. chapter_goal: target_word_count
        cursor = await conn.execute(
            "SELECT word_count_target FROM chapter_goals WHERE project_id=? AND chapter_number=?",
            (project_id, chapter_number),
        )
        row = await cursor.fetchone()
        target_word_count = row["word_count_target"] if row else 0
        metrics["target_word_count"] = target_word_count

        # 2. chapter_head + chapter_versions: word_count, version info
        cursor = await conn.execute(
            """SELECT h.accepted_version_id, h.current_version_id, h.status
            FROM chapter_heads h
            WHERE h.project_id=? AND h.chapter_number=?""",
            (project_id, chapter_number),
        )
        head_row = await cursor.fetchone()

        if head_row and head_row["accepted_version_id"]:
            cursor = await conn.execute(
                "SELECT * FROM chapter_versions WHERE version_id=?",
                (head_row["accepted_version_id"],),
            )
            version_row = await cursor.fetchone()
            if version_row:
                metrics["word_count"] = version_row["word_count"]
                metrics["budget_used_word"] = (
                    round(version_row["word_count"] / target_word_count, 3)
                    if target_word_count > 0
                    else 0.0
                )
                # generation_metadata
                try:
                    gen_meta = json.loads(version_row["generation_metadata"] or "{}")
                    metrics["token_budget_used"] = gen_meta.get("context_snapshot", {}).get(
                        "budget_used"
                    )
                    metrics["was_truncated"] = gen_meta.get("_word_count_truncated", False)
                    metrics["truncation_reason"] = gen_meta.get("_truncation_reason", "")
                    metrics["prompt_length"] = gen_meta.get("prompt_length", 0)
                except Exception:
                    pass

        # 3. revision 触发率: 统计 version_number > 1 的数量
        cursor = await conn.execute(
            "SELECT MAX(version_number) as max_ver FROM chapter_versions WHERE project_id=? AND chapter_number=?",
            (project_id, chapter_number),
        )
        rev_row = await cursor.fetchone()
        max_ver = rev_row["max_ver"] if rev_row else 1
        metrics["revision_count"] = max(0, (max_ver or 1) - 1)
        metrics["revision_triggered"] = metrics["revision_count"] > 0

        # 5. summary
        cursor = await conn.execute(
            "SELECT plot_summary FROM summaries WHERE project_id=? AND chapter_number=?",
            (project_id, chapter_number),
        )
        summary_row = await cursor.fetchone()
        if summary_row:
            metrics["summary_length"] = len(summary_row["plot_summary"] or "")

    return metrics


# ---------------------------------------------------------------------------
# Markdown 导出
# ---------------------------------------------------------------------------
async def _export_chapter_markdown(
    project_id: str, chapter_number: int, md_dir: Path, metrics: dict
) -> Path | None:
    from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository

    head_repo = ChapterHeadRepository()
    head = await head_repo.get(project_id, chapter_number)
    if head is None or not head.accepted_version_id:
        return None

    version_repo = ChapterVersionRepository()
    version = await version_repo.get(head.accepted_version_id)
    if version is None or not version.content:
        return None

    md_dir.mkdir(parents=True, exist_ok=True)
    md_path = md_dir / f"chapter_{chapter_number:02d}.md"

    frontmatter = {
        "title": f"第{chapter_number}章",
        "word_count": version.word_count,
        "scenes": len(version.scenes),
        "version": version.version_number,
        "target_word_count": metrics.get("target_word_count"),
        "budget_used_word": metrics.get("budget_used_word"),
        "revision_count": metrics.get("revision_count"),
    }

    lines = ["---"]
    for k, v in frontmatter.items():
        if v is None:
            continue
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")

    md_content = "\n".join(lines) + "\n\n" + version.content.strip() + "\n"
    md_path.write_text(md_content, encoding="utf-8")
    return md_path


async def _export_project_index(
    project_id: str, chapters: list[int], md_dir: Path, progress: ProgressState
) -> Path:
    from songyan.db.repository import ProjectRepository

    proj_repo = ProjectRepository()
    project = await proj_repo.get(project_id)
    title = project.title if project else "未知项目"

    total_wc = 0
    for ch in chapters:
        m = progress.chapter_metrics.get(str(ch), {})
        total_wc += m.get("word_count", 0)

    lines = [
        f"# {title}",
        "",
        f"- **项目 ID**: `{project_id}`",
        f"- **题材**: scifi",
        f"- **模式**: webnovel",
        f"- **总章节数**: {len(chapters)}",
        f"- **总字数**: {total_wc}",
        "",
        "## 章节列表",
        "",
    ]

    for ch in sorted(chapters):
        m = progress.chapter_metrics.get(str(ch), {})
        wc = m.get("word_count", "")
        target = m.get("target_word_count", "")
        rev = m.get("revision_count", 0)
        info_parts = []
        if wc:
            info_parts.append(f"{wc} 字")
        if target:
            info_parts.append(f"目标 {target}")
        if rev:
            info_parts.append(f"修订 {rev} 次")
        info = f"（{', '.join(info_parts)}）" if info_parts else ""
        lines.append(f"- [第{ch}章](chapters/chapter_{ch:02d}.md){info}")

    lines.append("")

    # 失败章节
    if progress.failed_chapters:
        lines.append("## 失败章节")
        lines.append("")
        for f in progress.failed_chapters:
            lines.append(f"- 第{f['chapter']}章: {f['last_error'][:80]}... (尝试 {f['attempts']} 次)")
        lines.append("")

    readme_path = md_dir.parent / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("\n".join(lines), encoding="utf-8")
    return readme_path


# ---------------------------------------------------------------------------
# 单章运行
# ---------------------------------------------------------------------------
async def _run_single_chapter(
    project_id: str,
    chapter_number: int,
    mode_id: str,
    output_dir: Path,
    progress: ProgressState,
) -> dict[str, Any]:
    """运行单章，收集 metrics.

    内部 run_project_pipeline 已含 2 次尝试 (on_failure='retry').
    外层不再额外重试，避免已成功但 metrics 收集失败时重新跑整章。
    """
    global LLM_CALLS
    chapter_llm_calls_before = len(LLM_CALLS)
    chapter_start = time.monotonic()

    try:
        await reset_checkpointer()

        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(chapter_number, chapter_number),
            mode_id=mode_id,
            auto_confirm=True,
            on_failure="retry",
            max_revision_rounds=2,
        )

        if chapter_number not in result.chapters_completed:
            last_error = f"Pipeline failed: chapters_failed={result.chapters_failed}, status={result.final_status}"
            elapsed = time.monotonic() - chapter_start
            progress.mark_failed(chapter_number, last_error, attempts=1)
            return {
                "success": False,
                "error": last_error,
                "elapsed_sec": round(elapsed, 1),
                "llm_calls": len(LLM_CALLS) - chapter_llm_calls_before,
            }

        # Pipeline 成功 — 收集 metrics（失败不影响成功状态）
        elapsed = time.monotonic() - chapter_start
        metrics: dict[str, Any] = {"chapter": chapter_number}
        try:
            metrics = await _collect_chapter_metrics(project_id, chapter_number, output_dir / "test.db")
        except Exception as exc:
            print(f"   ⚠️ Metrics 收集失败: {exc}")
            traceback.print_exc()

        metrics["elapsed_sec"] = round(elapsed, 1)
        metrics["llm_calls"] = len(LLM_CALLS) - chapter_llm_calls_before
        metrics["timestamp"] = datetime.now(timezone.utc).isoformat()

        # 计算该章 LLM 成本
        chapter_calls = LLM_CALLS[chapter_llm_calls_before:]
        raw_cost = estimate_cost_from_calls(chapter_calls)
        metrics["llm_cost_usd"] = round(raw_cost.get("total_usd", 0.0), 4) if isinstance(raw_cost, dict) else 0.0

        progress.mark_completed(chapter_number, metrics)
        return {"success": True, "metrics": metrics}

    except Exception as exc:
        last_error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
        elapsed = time.monotonic() - chapter_start
        progress.mark_failed(chapter_number, last_error, attempts=1)
        return {
            "success": False,
            "error": last_error,
            "elapsed_sec": round(elapsed, 1),
            "llm_calls": len(LLM_CALLS) - chapter_llm_calls_before,
        }


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------
def _generate_report(progress: ProgressState, total_elapsed: float, output_dir: Path):
    """生成 Markdown 报告."""
    completed = progress.completed_chapters
    failed = [f["chapter"] for f in progress.failed_chapters]
    skipped = progress.skipped_chapters

    # 字数统计
    word_counts = []
    budget_ratios = []
    revision_triggered_count = 0
    total_llm_calls = 0
    total_llm_cost = 0.0
    truncation_count = 0

    for ch in completed:
        m = progress.chapter_metrics.get(str(ch), {})
        wc = m.get("word_count", 0)
        target = m.get("target_word_count", 0)
        if wc and target:
            word_counts.append(wc)
            budget_ratios.append(wc / target)
        if m.get("revision_triggered"):
            revision_triggered_count += 1
        total_llm_calls += m.get("llm_calls", 0)
        total_llm_cost += m.get("llm_cost_usd", 0.0)
        if m.get("was_truncated"):
            truncation_count += 1

    # 达标率: ±20%
    pass_count = sum(1 for r in budget_ratios if 0.8 <= r <= 1.2)
    pass_rate = round(pass_count / len(budget_ratios) * 100, 1) if budget_ratios else 0.0

    lines = [
        "# Task 090a: Phase B Ch1-Ch20 端到端回流验证报告",
        "",
        f"- **生成时间**: {datetime.now(timezone.utc).isoformat()}",
        f"- **项目 ID**: `{progress.project_id}`",
        f"- **种子**: scifi_webnovel + scifi_ch1.md",
        f"- **模式**: {DEFAULT_MODE_ID}",
        "",
        "## 运行概况",
        "",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 完成章节 | {len(completed)} / 19 (Ch2-Ch20) |",
        f"| 失败章节 | {len(failed)} |",
        f"| 跳过章节 | {len(skipped)} |",
        f"| 总耗时 | {total_elapsed / 60:.1f} 分钟 |",
        f"| 总 LLM 调用 | {total_llm_calls} |",
        f"| 预估总成本 | ~¥{total_llm_cost * 7.2:.2f} |",
        "",
        "## 字数达标率",
        "",
        f"- **达标率（±20%）**: {pass_rate}% ({pass_count}/{len(budget_ratios)})",
        f"- **平均字数**: {sum(word_counts)//len(word_counts) if word_counts else 0} 字",
        f"- **字数范围**: {min(word_counts) if word_counts else 0} ~ {max(word_counts) if word_counts else 0} 字",
        f"- **平均 budget_used (word)**: {sum(budget_ratios)/len(budget_ratios):.3f}" if budget_ratios else "",
        "",
        "## Revision 统计",
        "",
        f"- **触发 revision 的章节**: {revision_triggered_count} / {len(completed)} ({round(revision_triggered_count/len(completed)*100,1)}%)",
        f"- **Writer 截断次数**: {truncation_count}",
        "",
        "## 逐章 Metrics",
        "",
        "| 章节 | 字数 | 目标 | budget | revision | 截断 | 耗时(s) | LLM调用 | 成本(¥) |",
        "|------|------|------|--------|----------|------|---------|---------|---------|",
    ]

    for ch in sorted(completed):
        m = progress.chapter_metrics.get(str(ch), {})
        wc = m.get("word_count", "-")
        target = m.get("target_word_count", "-")
        budget = m.get("budget_used_word", "-")
        rev = m.get("revision_count", 0)
        trunc = "是" if m.get("was_truncated") else "否"
        elapsed = m.get("elapsed_sec", "-")
        calls = m.get("llm_calls", "-")
        cost = f"¥{m.get('llm_cost_usd', 0)*7.2:.2f}" if m.get("llm_cost_usd") else "-"
        lines.append(
            f"| Ch{ch} | {wc} | {target} | {budget} | {rev} | {trunc} | {elapsed} | {calls} | {cost} |"
        )

    lines.extend(["", "## 失败详情", ""])
    if failed:
        for f in progress.failed_chapters:
            lines.append(f"- **Ch{f['chapter']}**: {f['last_error']} (尝试 {f['attempts']} 次)")
    else:
        lines.append("无失败章节。")

    lines.extend(["", "## 异常分析", ""])

    # 超标章节
    over_budget = [ch for ch in completed if (progress.chapter_metrics.get(str(ch), {}).get("budget_used_word") or 0) > 1.2]
    if over_budget:
        lines.append(f"- **字数超标（>1.2x）**: Ch{', '.join(str(c) for c in over_budget)}")
    else:
        lines.append("- **字数超标**: 无")

    # 低于下限
    under_budget = [ch for ch in completed if (progress.chapter_metrics.get(str(ch), {}).get("budget_used_word") or 0) < 0.8]
    if under_budget:
        lines.append(f"- **字数不足（<0.8x）**: Ch{', '.join(str(c) for c in under_budget)}")
    else:
        lines.append("- **字数不足**: 无")

    # settlement needs review
    needs_review = [ch for ch in completed if progress.chapter_metrics.get(str(ch), {}).get("settlement_needs_review")]
    if needs_review:
        lines.append(f"- **Settlement 需人工复核**: Ch{', '.join(str(c) for c in needs_review)}")
    else:
        lines.append("- **Settlement 需人工复核**: 无")

    lines.append("")

    report_path = output_dir / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------
async def _main() -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/task_090a_resilient_runner.py",
        description="Task 090a: Phase B Ch1-Ch20 端到端回流验证",
    )
    parser.add_argument("--resume-dir", help="恢复运行的输出目录")
    parser.add_argument("--start", type=int, default=DEFAULT_START_CHAPTER, help="起始章节（默认2）")
    parser.add_argument("--end", type=int, default=DEFAULT_END_CHAPTER, help="结束章节（默认20）")
    parser.add_argument("--mode-id", default=DEFAULT_MODE_ID, help="创作模式")
    parser.add_argument("--md-dir", help="Markdown 导出目录")
    parser.add_argument("--dry-run", action="store_true", help="验证配置后退出")
    args = parser.parse_args()

    print("=" * 60)
    print("Task 090a: Phase B Ch1-Ch20 端到端回流验证")
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

    # 输出目录
    if args.resume_dir:
        output_dir = Path(args.resume_dir)
    else:
        output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    progress_path = output_dir / "progress.json"
    progress = ProgressState.load(progress_path)

    # 数据库路径
    db_path = output_dir / "test.db"
    settings.database_url = f"sqlite:///{db_path}"

    # 初始化数据库（仅当不存在时）
    if not db_path.exists() or not progress.project_id:
        print(f"\n📁 初始化新运行")
        print(f"   输出目录: {output_dir.resolve()}")
        print(f"   数据库: {db_path}")
        await init_schema()
        print("   数据库 schema 初始化完成")
    else:
        print(f"\n📁 恢复已有运行")
        print(f"   输出目录: {output_dir.resolve()}")
        print(f"   项目 ID: {progress.project_id}")
        print(f"   已完成: {sorted(progress.completed_chapters)}")
        if progress.failed_chapters:
            print(f"   已失败: {[f['chapter'] for f in progress.failed_chapters]}")

    # Markdown 目录
    md_dir = Path(args.md_dir) if args.md_dir else DEFAULT_MD_DIR
    md_dir.mkdir(parents=True, exist_ok=True)

    # Patch LLM 调用
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

    # 导入种子项目（如果不存在）
    if not progress.project_id:
        print("\n📥 导入种子项目...")
        project_id = await import_seed_project(SEED_CONFIG_PATH)
        progress.project_id = project_id
        print(f"   项目 ID: {project_id}")

        print("📥 导入种子章节（Chapter 1）...")
        await import_seed_chapter(project_id, SEED_CHAPTER_PATH, chapter_number=1)
        print("   完成")

        # 保存初始进度
        progress.save(progress_path)
    else:
        project_id = progress.project_id

    # 检查 Chapter 1 是否存在（如果不存在则重新导入）
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT 1 FROM chapter_heads WHERE project_id=? AND chapter_number=1",
            (project_id,),
        )
        if not await cursor.fetchone():
            print("📥 重新导入种子章节（Chapter 1）...")
            await import_seed_chapter(project_id, SEED_CHAPTER_PATH, chapter_number=1)
            print("   完成")

    print(f"\n🎯 开始验证 Ch{args.start} → Ch{args.end}")
    print(f"   预估调用 ~{(args.end - args.start + 1) * 7} 次 LLM")
    print("   按 Ctrl+C 可随时中断（不会丢失进度）\n")

    total_start = time.monotonic()
    completed_before = set(progress.completed_chapters)

    # 全局 LLM 调用追踪
    global LLM_CALLS
    LLM_CALLS.clear()

    with contextlib.ExitStack() as stack:
        for target, agent_name in targets:
            stack.enter_context(patch(target, _make_wrapper(agent_name)))

        for chapter_number in range(args.start, args.end + 1):
            if progress.is_done(chapter_number):
                print(f"⏭️  Ch{chapter_number} 已处理，跳过")
                continue

            print(f"\n{'='*60}")
            print(f"🚀 Chapter {chapter_number} / {args.end}")
            print(f"{'='*60}")

            chapter_start = time.monotonic()
            try:
                result = await _run_single_chapter(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    mode_id=args.mode_id,
                    output_dir=output_dir,
                    progress=progress,
                )
            except KeyboardInterrupt:
                print("\n\n⚠️ 用户中断")
                progress.save(progress_path)
                print(f"   进度已保存至: {progress_path}")
                return 130

            chapter_elapsed = time.monotonic() - chapter_start

            if result["success"]:
                metrics = result["metrics"]
                print(f"\n✅ Ch{chapter_number} 成功 | {chapter_elapsed:.1f}s")
                print(f"   字数: {metrics.get('word_count', '-')} / 目标 {metrics.get('target_word_count', '-')}")
                print(f"   budget_used: {metrics.get('budget_used_word', '-')}")
                print(f"   revision: {metrics.get('revision_count', 0)} 次")
                print(f"   LLM 调用: {metrics.get('llm_calls', 0)}")

                # 导出 Markdown
                try:
                    md_path = await _export_chapter_markdown(
                        project_id, chapter_number, md_dir, metrics
                    )
                    if md_path:
                        print(f"   📝 Markdown: {md_path}")
                except Exception as exc:
                    print(f"   ⚠️ Markdown 导出失败: {exc}")

            else:
                print(f"\n❌ Ch{chapter_number} 失败 | {chapter_elapsed:.1f}s")
                print(f"   错误: {result['error'][:120]}")
                # 标记为跳过，继续下一章
                progress.mark_skipped(chapter_number)

            # 保存进度（每章后立即保存，不丢失）
            progress.save(progress_path)
            print(f"   💾 进度已保存")

            # 更新项目索引
            try:
                await _export_project_index(
                    project_id,
                    sorted(progress.completed_chapters),
                    md_dir,
                    progress,
                )
            except Exception as exc:
                print(f"   ⚠️ 索引更新失败: {exc}")

            # 打印累计进度
            total_elapsed = time.monotonic() - total_start
            completed_now = len(progress.completed_chapters)
            remaining = args.end - args.start + 1 - completed_now
            avg_time = total_elapsed / max(completed_now - len(completed_before), 1)
            eta = avg_time * remaining
            print(f"   📊 累计: {completed_now}/{args.end - args.start + 1} 完成, "
                  f"{len(progress.failed_chapters)} 失败, "
                  f"ETA ~{eta/60:.0f}min")

    # ------------------------------------------------------------------
    # 收尾：生成报告
    # ------------------------------------------------------------------
    total_elapsed = time.monotonic() - total_start
    print("\n" + "=" * 60)
    print("运行结束，生成报告...")
    print("=" * 60)

    report_path = _generate_report(progress, total_elapsed, output_dir)
    print(f"\n📄 报告已保存: {report_path}")

    # 保存完整 LLM 调用日志
    llm_log_path = output_dir / "llm_calls.jsonl"
    with llm_log_path.open("w", encoding="utf-8") as f:
        for call in LLM_CALLS:
            f.write(json.dumps(call, ensure_ascii=False) + "\n")
    print(f"📞 LLM 日志: {llm_log_path}")

    # 打印摘要
    completed = progress.completed_chapters
    failed = progress.failed_chapters
    print(f"\n{'='*60}")
    print("📊 最终摘要")
    print(f"{'='*60}")
    print(f"完成: {len(completed)} 章")
    print(f"失败: {len(failed)} 章")
    if failed:
        for f in failed:
            print(f"  - Ch{f['chapter']}: {f['last_error'][:80]}")
    print(f"总耗时: {total_elapsed/60:.1f} 分钟")
    print(f"总 LLM 调用: {len(LLM_CALLS)}")
    raw_cost = estimate_cost_from_calls(LLM_CALLS)
    print(f"预估总成本: {format_cost_estimate(raw_cost)}")

    if not failed and len(completed) == (args.end - args.start + 1):
        print("\n🎉 全部章节验证通过！")
        return 0
    else:
        print(f"\n⚠️ 部分章节未通过（{len(failed)} 失败, {len(progress.skipped_chapters)} 跳过）")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(_main()))
    except KeyboardInterrupt:
        print("\n已取消。进度已在每章后保存，可重新运行脚本恢复。")
        sys.exit(130)

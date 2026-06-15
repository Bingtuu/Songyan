#!/usr/bin/env python3
"""Task 091: Phase B Ch21-Ch50 + Ch51-Ch70 端到端验证 — Resilient Runner.

核心设计原则:
- 断点续跑: progress.json 保存状态, 重启自动恢复
- 失败不阻塞: 单章失败后记录并继续下一章
- 详细 metrics: 每章收集字数/budget/revision/health/lifecycle/耗时/错误
- 生命周期统计: 每章 accept 后收集 active/dormant/archived 分布
- 分段报告: Ch1-Ch20 / Ch21-Ch50 / Ch51-Ch70 分别统计

用法:
    python scripts/task_091_resilient_runner.py [--resume-dir DIR] [--start 1] [--end 70]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Row
from typing import Any
from unittest.mock import patch

# Windows 控制台 UTF-8 编码修复
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 确保项目根目录在 sys.path 中
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
DEFAULT_END_CHAPTER = 70
DEFAULT_OUTPUT_DIR = Path("evals/output/task_091_scifi_webnovel")
DEFAULT_MD_DIR = Path("projects/task_091_scifi_novel/chapters")

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
                    metrics["_rewrite_reason"] = gen_meta.get("_rewrite_reason", "")
                    metrics["revision_rounds"] = gen_meta.get("revision_rounds", 0)
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

        # 4. continuity health_score
        cursor = await conn.execute(
            """SELECT overall_health_score, overdue_foreshadowings, orphaned_settings
            FROM continuity_reports
            WHERE project_id = ? AND checked_up_to_chapter = ?
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, chapter_number),
        )
        cont_row = await cursor.fetchone()
        if cont_row:
            metrics["health_score"] = cont_row["overall_health_score"]
            try:
                metrics["overdue_count"] = len(json.loads(cont_row["overdue_foreshadowings"] or "[]"))
            except Exception:
                metrics["overdue_count"] = 0
            try:
                metrics["orphaned_count"] = len(json.loads(cont_row["orphaned_settings"] or "[]"))
            except Exception:
                metrics["orphaned_count"] = 0
        else:
            metrics["health_score"] = None
            metrics["overdue_count"] = None
            metrics["orphaned_count"] = None

        # 5. review report issues
        cursor = await conn.execute(
            """SELECT issues, overall_score FROM review_reports
            WHERE chapter_version_id IN (
                SELECT version_id FROM chapter_versions
                WHERE project_id = ? AND chapter_number = ? AND version_type = 'accepted'
            )
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, chapter_number),
        )
        review_row = await cursor.fetchone()
        if review_row:
            try:
                issues = json.loads(review_row["issues"] or "[]")
                metrics["critical_count"] = sum(1 for i in issues if i.get("severity") == "critical")
                metrics["major_count"] = sum(1 for i in issues if i.get("severity") == "major")
                metrics["minor_count"] = sum(1 for i in issues if i.get("severity") == "minor")
                metrics["overall_score"] = review_row["overall_score"]
            except Exception:
                metrics["critical_count"] = 0
                metrics["major_count"] = 0
                metrics["minor_count"] = 0
                metrics["overall_score"] = None
        else:
            metrics["critical_count"] = None
            metrics["major_count"] = None
            metrics["minor_count"] = None
            metrics["overall_score"] = None

        # 6. summary
        cursor = await conn.execute(
            "SELECT plot_summary FROM summaries WHERE project_id=? AND chapter_number=?",
            (project_id, chapter_number),
        )
        summary_row = await cursor.fetchone()
        if summary_row:
            metrics["summary_length"] = len(summary_row["plot_summary"] or "")

    return metrics


# ---------------------------------------------------------------------------
# 生命周期统计收集
# ---------------------------------------------------------------------------
async def _collect_lifecycle_stats(project_id: str) -> dict[str, int]:
    """收集项目下所有生命周期表的状态分布统计.

    V4.0 Task 091: 用于生命周期效果验证。
    """
    stats: dict[str, int] = {}
    tables = [
        ("setting_snapshots", "settings"),
        ("foreshadowings", "foreshadowings"),
        ("human_marks", "marks"),
    ]
    async with get_db() as conn:
        for table, key in tables:
            for status in ("active", "dormant", "archived"):
                cursor = await conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE project_id = ? AND lifecycle_status = ?",
                    (project_id, status),
                )
                row = await cursor.fetchone()
                stats[f"{key}_{status}"] = row[0] if row else 0

        # character_states 无 project_id，需 JOIN characters
        for status in ("active", "dormant", "archived"):
            cursor = await conn.execute(
                """SELECT COUNT(*) FROM character_states cs
                JOIN characters c ON cs.character_id = c.character_id
                WHERE c.project_id = ? AND cs.lifecycle_status = ?""",
                (project_id, status),
            )
            row = await cursor.fetchone()
            stats[f"character_states_{status}"] = row[0] if row else 0

    return stats


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
    """运行单章，收集 metrics."""
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

        # Pipeline 成功 — 收集 metrics
        elapsed = time.monotonic() - chapter_start
        metrics: dict[str, Any] = {"chapter": chapter_number}
        try:
            metrics = await _collect_chapter_metrics(project_id, chapter_number, output_dir / "test.db")
        except Exception as exc:
            print(f"   ⚠️ Metrics 收集失败: {exc}")
            traceback.print_exc()

        # Task 098: 用管道状态的累计修订次数覆盖 DB 的累计值（DB 的 MAX(version_number) 跨运行累计）
        try:
            _total_rev = result.state.get("_total_revision_count")
            if _total_rev is not None and _total_rev > 0:
                metrics["revision_count"] = _total_rev
        except AttributeError:
            pass

        # 收集生命周期统计
        try:
            lifecycle = await _collect_lifecycle_stats(project_id)
            metrics["lifecycle"] = lifecycle
        except Exception as exc:
            print(f"   ⚠️ Lifecycle 统计收集失败: {exc}")
            metrics["lifecycle"] = {}

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

    # 分段统计
    def _segment_stats(chapters: list[int]) -> dict:
        word_counts = []
        budget_ratios = []
        revision_triggered_count = 0
        truncation_count = 0
        health_scores = []
        token_budgets = []

        for ch in chapters:
            m = progress.chapter_metrics.get(str(ch), {})
            wc = m.get("word_count", 0)
            target = m.get("target_word_count", 0)
            if wc and target:
                word_counts.append(wc)
                budget_ratios.append(wc / target)
            if m.get("revision_triggered"):
                revision_triggered_count += 1
            if m.get("was_truncated"):
                truncation_count += 1
            hs = m.get("health_score")
            if hs is not None:
                health_scores.append(hs)
            tb = m.get("token_budget_used")
            if tb is not None:
                token_budgets.append(tb)

        pass_count = sum(1 for r in budget_ratios if 0.8 <= r <= 1.2)
        return {
            "count": len(word_counts),
            "pass_rate": round(pass_count / len(budget_ratios) * 100, 1) if budget_ratios else 0.0,
            "avg_word_count": sum(word_counts) // len(word_counts) if word_counts else 0,
            "min_word_count": min(word_counts) if word_counts else 0,
            "max_word_count": max(word_counts) if word_counts else 0,
            "avg_budget_ratio": sum(budget_ratios) / len(budget_ratios) if budget_ratios else 0.0,
            "max_budget_ratio": max(budget_ratios) if budget_ratios else 0.0,
            "revision_rate": round(revision_triggered_count / len(chapters) * 100, 1) if chapters else 0.0,
            "truncation_rate": round(truncation_count / len(chapters) * 100, 1) if chapters else 0.0,
            "avg_health_score": round(sum(health_scores) / len(health_scores), 2) if health_scores else None,
            "avg_token_budget": round(sum(token_budgets) / len(token_budgets), 3) if token_budgets else None,
            "max_token_budget": max(token_budgets) if token_budgets else None,
        }

    ch1_20 = [c for c in completed if 1 <= c <= 20]
    ch21_50 = [c for c in completed if 21 <= c <= 50]
    ch51_70 = [c for c in completed if 51 <= c <= 70]

    stats_1_20 = _segment_stats(ch1_20)
    stats_21_50 = _segment_stats(ch21_50)
    stats_51_70 = _segment_stats(ch51_70)
    stats_all = _segment_stats(completed)

    lines = [
        "# Task 091: Phase B Ch21-Ch50 + Ch51-Ch70 端到端验证报告",
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
        f"| 完成章节 | {len(completed)} |",
        f"| 失败章节 | {len(failed)} |",
        f"| 跳过章节 | {len(skipped)} |",
        f"| 总耗时 | {total_elapsed / 60:.1f} 分钟 |",
        f"| 总 LLM 调用 | {len(LLM_CALLS)} |",
        "",
        "## 分段统计",
        "",
        "| 指标 | Ch1-Ch20 | Ch21-Ch50 | Ch51-Ch70 | 全部 |",
        "|------|----------|-----------|-----------|------|",
        f"| 完成章节 | {stats_1_20['count']} | {stats_21_50['count']} | {stats_51_70['count']} | {stats_all['count']} |",
        f"| 字数达标率(±20%) | {stats_1_20['pass_rate']}% | {stats_21_50['pass_rate']}% | {stats_51_70['pass_rate']}% | {stats_all['pass_rate']}% |",
        f"| 平均字数 | {stats_1_20['avg_word_count']} | {stats_21_50['avg_word_count']} | {stats_51_70['avg_word_count']} | {stats_all['avg_word_count']} |",
        f"| 字数范围 | {stats_1_20['min_word_count']}-{stats_1_20['max_word_count']} | {stats_21_50['min_word_count']}-{stats_21_50['max_word_count']} | {stats_51_70['min_word_count']}-{stats_51_70['max_word_count']} | {stats_all['min_word_count']}-{stats_all['max_word_count']} |",
        f"| 平均 budget_used(word) | {stats_1_20['avg_budget_ratio']:.3f} | {stats_21_50['avg_budget_ratio']:.3f} | {stats_51_70['avg_budget_ratio']:.3f} | {stats_all['avg_budget_ratio']:.3f} |",
        f"| 最大 budget_used(word) | {stats_1_20['max_budget_ratio']:.3f} | {stats_21_50['max_budget_ratio']:.3f} | {stats_51_70['max_budget_ratio']:.3f} | {stats_all['max_budget_ratio']:.3f} |",
        f"| Revision 触发率 | {stats_1_20['revision_rate']}% | {stats_21_50['revision_rate']}% | {stats_51_70['revision_rate']}% | {stats_all['revision_rate']}% |",
        f"| Writer 截断率 | {stats_1_20['truncation_rate']}% | {stats_21_50['truncation_rate']}% | {stats_51_70['truncation_rate']}% | {stats_all['truncation_rate']}% |",
        f"| 平均 health_score | {stats_1_20['avg_health_score'] or '-'} | {stats_21_50['avg_health_score'] or '-'} | {stats_51_70['avg_health_score'] or '-'} | {stats_all['avg_health_score'] or '-'} |",
        f"| 平均 token_budget | {stats_1_20['avg_token_budget'] or '-'} | {stats_21_50['avg_token_budget'] or '-'} | {stats_51_70['avg_token_budget'] or '-'} | {stats_all['avg_token_budget'] or '-'} |",
        f"| 最大 token_budget | {stats_1_20['max_token_budget'] or '-'} | {stats_21_50['max_token_budget'] or '-'} | {stats_51_70['max_token_budget'] or '-'} | {stats_all['max_token_budget'] or '-'} |",
        "",
        "## 验收标准检查",
        "",
        f"| 验收项 | 目标 | Ch21-Ch50 实际 | 达标 |",
        f"|--------|------|----------------|------|",
        f"| 字数达标率 | > 65% | {stats_21_50['pass_rate']}% | {'✅' if stats_21_50['pass_rate'] >= 65 else '❌'} |",
        f"| budget_used 平均 | < 1.4 | {stats_21_50['avg_budget_ratio']:.3f} | {'✅' if stats_21_50['avg_budget_ratio'] < 1.4 else '❌'} |",
        f"| budget_used 最大 | < 1.6 | {stats_21_50['max_budget_ratio']:.3f} | {'✅' if stats_21_50['max_budget_ratio'] < 1.6 else '❌'} |",
        f"| health_score 平均 | >= 3.0 | {stats_21_50['avg_health_score'] or '-'} | {'✅' if stats_21_50['avg_health_score'] is not None and stats_21_50['avg_health_score'] >= 3.0 else '❌'} |",
        "",
        "## 字数达标率详情",
        "",
        "| 章节 | 字数 | 目标 | budget | 达标 | revision | 截断 | health | token_budget |",
        "|------|------|------|--------|------|----------|------|--------|-------------|",
    ]

    for ch in sorted(completed):
        m = progress.chapter_metrics.get(str(ch), {})
        wc = m.get("word_count", "-")
        target = m.get("target_word_count", "-")
        budget = m.get("budget_used_word", "-")
        in_range = ""
        if isinstance(budget, (int, float)) and budget:
            in_range = "✅" if 0.8 <= budget <= 1.2 else "❌"
        rev = m.get("revision_count", 0)
        trunc = "是" if m.get("was_truncated") else ""
        health = m.get("health_score", "-")
        if isinstance(health, float):
            health = f"{health:.1f}"
        token_b = m.get("token_budget_used", "-")
        if isinstance(token_b, float):
            token_b = f"{token_b:.2f}"
        lines.append(
            f"| Ch{ch} | {wc} | {target} | {budget} | {in_range} | {rev} | {trunc} | {health} | {token_b} |"
        )

    lines.extend(["", "## 失败详情", ""])
    if failed:
        for f_item in progress.failed_chapters:
            lines.append(f"- **Ch{f_item['chapter']}**: {f_item['last_error']} (尝试 {f_item['attempts']} 次)")
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

    lines.append("")

    report_path = output_dir / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _generate_lifecycle_report(progress: ProgressState, output_dir: Path):
    """生成生命周期趋势报告 (lifecycle_trend.json + markdown)."""
    lifecycle_data = []
    for ch in sorted(progress.completed_chapters):
        m = progress.chapter_metrics.get(str(ch), {})
        lifecycle = m.get("lifecycle", {})
        lifecycle_data.append({
            "chapter": ch,
            "settings_active": lifecycle.get("settings_active", 0),
            "settings_dormant": lifecycle.get("settings_dormant", 0),
            "settings_archived": lifecycle.get("settings_archived", 0),
            "foreshadowings_active": lifecycle.get("foreshadowings_active", 0),
            "foreshadowings_dormant": lifecycle.get("foreshadowings_dormant", 0),
            "foreshadowings_archived": lifecycle.get("foreshadowings_archived", 0),
            "marks_active": lifecycle.get("marks_active", 0),
            "marks_dormant": lifecycle.get("marks_dormant", 0),
            "marks_archived": lifecycle.get("marks_archived", 0),
            "character_states_active": lifecycle.get("character_states_active", 0),
            "character_states_dormant": lifecycle.get("character_states_dormant", 0),
            "character_states_archived": lifecycle.get("character_states_archived", 0),
        })

    # Save JSON
    json_path = output_dir / "lifecycle_trend.json"
    json_path.write_text(json.dumps(lifecycle_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate markdown table
    lines = [
        "# 生命周期趋势报告",
        "",
        "| 章节 | settings(A/D/Ar) | foreshadowings(A/D/Ar) | marks(A/D/Ar) | char_states(A/D/Ar) |",
        "|------|------------------|------------------------|---------------|---------------------|",
    ]
    for item in lifecycle_data:
        s = f"{item['settings_active']}/{item['settings_dormant']}/{item['settings_archived']}"
        f = f"{item['foreshadowings_active']}/{item['foreshadowings_dormant']}/{item['foreshadowings_archived']}"
        m = f"{item['marks_active']}/{item['marks_dormant']}/{item['marks_archived']}"
        c = f"{item['character_states_active']}/{item['character_states_dormant']}/{item['character_states_archived']}"
        lines.append(f"| Ch{item['chapter']} | {s} | {f} | {m} | {c} |")

    lines.append("")
    lines.append("## 分析")
    lines.append("")

    if len(lifecycle_data) >= 2:
        first = lifecycle_data[0]
        last = lifecycle_data[-1]
        total_first = sum(v for k, v in first.items() if k != "chapter")
        total_last = sum(v for k, v in last.items() if k != "chapter")
        active_first = first["settings_active"] + first["foreshadowings_active"] + first["marks_active"] + first["character_states_active"]
        active_last = last["settings_active"] + last["foreshadowings_active"] + last["marks_active"] + last["character_states_active"]
        lines.append(f"- **首章总数据量**: {total_first}")
        lines.append(f"- **末章总数据量**: {total_last}")
        lines.append(f"- **首章 active 占比**: {active_first/total_first*100:.1f}%" if total_first > 0 else "- **首章 active 占比**: N/A")
        lines.append(f"- **末章 active 占比**: {active_last/total_last*100:.1f}%" if total_last > 0 else "- **末章 active 占比**: N/A")

    md_path = output_dir / "lifecycle_report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------
async def _main() -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/task_091_resilient_runner.py",
        description="Task 091: Phase B Ch21-Ch50 + Ch51-Ch70 端到端验证",
    )
    parser.add_argument("--resume-dir", help="恢复运行的输出目录")
    parser.add_argument("--start", type=int, default=DEFAULT_START_CHAPTER, help="起始章节（默认2）")
    parser.add_argument("--end", type=int, default=DEFAULT_END_CHAPTER, help="结束章节（默认70）")
    parser.add_argument("--mode-id", default=DEFAULT_MODE_ID, help="创作模式")
    parser.add_argument("--md-dir", help="Markdown 导出目录")
    parser.add_argument("--dry-run", action="store_true", help="验证配置后退出")
    args = parser.parse_args()

    print("=" * 60)
    print("Task 091: Phase B Ch21-Ch50 + Ch51-Ch70 端到端验证")
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
        print(f"   数据库: {db_path}")
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

    # 运行数据库迁移（新旧 DB 都执行，幂等）
    try:
        from songyan.db.migrations import run_migrations
        async with get_db() as conn:
            await run_migrations(conn)
    except Exception as exc:
        print(f"   ⚠️ 数据库迁移失败（非致命）: {exc}")

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
                print(f"   health_score: {metrics.get('health_score', '-')}")
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
    print(f"\n📄 主报告已保存: {report_path}")

    lifecycle_json, lifecycle_md = _generate_lifecycle_report(progress, output_dir)
    print(f"📊 生命周期趋势: {lifecycle_json}")
    print(f"📊 生命周期报告: {lifecycle_md}")

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
        for f_item in failed:
            print(f"  - Ch{f_item['chapter']}: {f_item['last_error'][:80]}")
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



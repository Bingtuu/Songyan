"""Task 172a.7: multi-genre short-window validation with full quality metrics.

Runs a genre template for Ch1..end and collects the V8 acceptance metrics:
- accepted rate, T9 hard issues
- budget_used peak, ContextEmergency count, budget-ratio halt
- overdue foreshadowing (continuity), CED (consistency error density)

Unlike run_172_short_window.py this keeps the DB long enough to query
context_snapshots + continuity, and reports per-chapter budget curve.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.evals.text_cleanliness import collect_text_cleanliness_metrics
from songyan.exceptions import AutoHaltException
from songyan.llm.client import aclose_llm_clients
from songyan.models import GateConfig
from songyan.project_templates import ProjectInitializer, ProjectTemplateLoader
from songyan.utils.logging_setup import configure_logging
from songyan.utils.process_exit import force_exit_after_run_if_requested
from songyan.workflows.phase2_graph import run_project_pipeline


def _word_count(content: str) -> int:
    chinese = len(re.findall(r"[\u4e00-\u9fff]", content))
    other = len(re.findall(r"[a-zA-Z0-9]+", content))
    return chinese + other


async def _budget_metrics(project_id: str, end: int) -> dict[str, object]:
    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT chapter_number, budget_used, context_emergency,
                      budget_used_before_emergency
               FROM context_snapshots
               WHERE project_id = ? AND chapter_number BETWEEN 1 AND ?
               ORDER BY chapter_number""",
            (project_id, end),
        )
        rows = await cursor.fetchall()
    per_chapter: dict[int, float] = {}
    emergency_count = 0
    peak_before_emergency = 0.0
    for row in rows:
        ch = int(row[0])
        used = float(row[1] or 0.0)
        per_chapter[ch] = max(per_chapter.get(ch, 0.0), used)
        if row[2]:
            emergency_count += 1
        if row[3] is not None:
            peak_before_emergency = max(peak_before_emergency, float(row[3]))
    return {
        "budget_used_peak": round(max(per_chapter.values()), 4) if per_chapter else 0.0,
        "budget_used_before_emergency_peak": round(peak_before_emergency, 4),
        "context_emergency_count": emergency_count,
        "budget_curve": {k: round(v, 3) for k, v in sorted(per_chapter.items())},
    }


async def _overdue_foreshadowing(project_id: str, up_to: int) -> int:
    """Count foreshadowings whose expected chapter passed but not resolved."""
    async with get_db() as conn:
        cursor = await conn.execute("PRAGMA table_info(foreshadowings)")
        cols = {row[1] for row in await cursor.fetchall()}
        expected_col = "expected_payoff_chapter" if "expected_payoff_chapter" in cols else None
        if expected_col is None:
            for candidate in ("expected_resolve_chapter", "target_chapter", "payoff_chapter"):
                if candidate in cols:
                    expected_col = candidate
                    break
        if expected_col is None:
            return -1
        cursor = await conn.execute(
            f"""SELECT COUNT(*) FROM foreshadowings
                WHERE project_id = ? AND {expected_col} IS NOT NULL
                  AND {expected_col} < ? AND status != 'resolved'""",
            (project_id, up_to),
        )
        row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def _ced(project_id: str, end: int) -> dict[str, object]:
    """Consistency Error Density = (critical+major issues w/ evidence) / total words.

    Genre-neutral: counts persisted review issues; excludes sci-fi-only observe
    path (172d ensures observe is genre-correct, but CED uses live review issues).
    """
    head_repo = ChapterHeadRepository()
    version_repo = ChapterVersionRepository()
    total_words = 0
    for ch in range(1, end + 1):
        head = await head_repo.get(project_id, ch)
        if head and head.status == "accepted" and head.accepted_version_id:
            v = await version_repo.get(head.accepted_version_id)
            if v:
                total_words += _word_count(v.content)
    issue_count = 0
    async with get_db() as conn:
        cursor = await conn.execute("PRAGMA table_info(review_reports)")
        cols = {row[1] for row in await cursor.fetchall()}
        if "issues" in cols:
            # review_reports keyed by chapter_version_id -> join to project via versions
            cursor = await conn.execute(
                """SELECT rr.issues FROM review_reports rr
                   JOIN chapter_versions cv ON cv.version_id = rr.chapter_version_id
                   WHERE cv.project_id = ?""",
                (project_id,),
            )
            for row in await cursor.fetchall():
                try:
                    issues = json.loads(row[0] or "[]")
                except (json.JSONDecodeError, TypeError):
                    continue
                for issue in issues:
                    sev = str(issue.get("severity", "")).lower()
                    if sev in ("critical", "major") and issue.get("evidence_quote"):
                        issue_count += 1
    ced = round(issue_count / total_words * 1000, 4) if total_words else 0.0
    return {
        "ced_per_1k_words": ced,
        "evidence_issue_count": issue_count,
        "total_words": total_words,
    }


async def run_for_template(template_id: str, end: int, retries: int = 2) -> dict[str, object]:
    safe_id = re.sub(r"[^\w-]", "_", template_id)
    tmpdir = tempfile.mkdtemp(prefix=f"task172a7_{safe_id}_")
    settings.database_url = f"sqlite:///{tmpdir}/songyan.db"

    template = ProjectTemplateLoader().load(template_id)
    project_id, project = await ProjectInitializer.from_template(template)

    gate_config = GateConfig.for_mode("enforce")
    # halt 自动重试：LLM 随机波动（修订不收敛/hook 误伤等）触发的 AutoHalt
    # 可通过 resume 从失败章重新生成恢复；重试耗尽才向上抛出。
    # tmpdir 在整个重试循环中复用，保证 resume 能读到已 accept 章节。
    result = None
    for attempt in range(retries + 1):
        try:
            result = await run_project_pipeline(
                project_id=project_id,
                chapter_range=(1, end),
                mode_id=project.mode_id,
                auto_confirm=True,
                on_failure="isolate",
                gate_config=gate_config,
                resume=attempt > 0,
            )
            break
        except AutoHaltException as exc:
            print(f"[retry] AutoHalt attempt {attempt + 1}/{retries + 1}: {exc}")
            if attempt >= retries:
                raise
    assert result is not None  # noqa: S101

    t9 = await collect_text_cleanliness_metrics(project_id, 1, end)
    t9_count = sum(
        m.meta_tag_leak_count + m.duplicate_paragraph_count + m.timeline_conflict_count
        for m in t9
    )
    budget = await _budget_metrics(project_id, end)
    overdue = await _overdue_foreshadowing(project_id, end)
    ced = await _ced(project_id, end)

    return {
        "template_id": template_id,
        "end": end,
        "completed": result.chapters_completed,
        "failed": result.chapters_failed,
        "status": result.final_status,
        "accepted_rate": round(len(result.chapters_completed) / end, 3) if end else 0.0,
        "t9_issue_count": t9_count,
        "overdue_foreshadowing": overdue,
        **budget,
        **ced,
    }


def main() -> None:
    configure_logging(settings.log_level, file_level=settings.log_file_level)
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", nargs="+", required=True)
    parser.add_argument("--end", type=int, default=10)
    parser.add_argument("--retries", type=int, default=2, help="AutoHalt 后自动 resume 重试次数")
    parser.add_argument("--output", default=".tmp/task172a7_validation.json")
    args = parser.parse_args()

    results = []
    for template_id in args.templates:
        print(f"\n=== {template_id} --end {args.end} ===")
        try:
            summary = asyncio.run(run_for_template(template_id, args.end, args.retries))
            results.append(summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        except Exception as exc:  # noqa: BLE001
            results.append({"template_id": template_id, "error": str(exc)})
            print(f"ERROR: {exc}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved to {out}")
    asyncio.run(aclose_llm_clients())
    force_exit_after_run_if_requested()


if __name__ == "__main__":
    main()

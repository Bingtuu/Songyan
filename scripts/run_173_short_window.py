"""Task 173 短章验证：为每个体裁跑 Ch1-Ch3，检查 completed/T9/字数."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.db.connection import get_db_path
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.evals.text_cleanliness import collect_text_cleanliness_metrics
from songyan.models import GateConfig
from songyan.project_templates import ProjectInitializer, ProjectTemplateLoader
from songyan.workflows.phase2_graph import run_project_pipeline


async def _accepted_word_counts(project_id: str, end_chapter: int) -> dict[int, int]:
    """Return accepted chapter word counts (Chinese characters) for Ch1..end."""
    head_repo = ChapterHeadRepository()
    version_repo = ChapterVersionRepository()
    counts: dict[int, int] = {}
    for chapter_number in range(1, end_chapter + 1):
        head = await head_repo.get(project_id, chapter_number)
        if head is None or head.status != "accepted" or not head.accepted_version_id:
            continue
        version = await version_repo.get(head.accepted_version_id)
        if version is None:
            continue
        counts[chapter_number] = len(version.content)
    return counts


async def run_for_template(template_id: str, end_chapter: int = 3) -> dict[str, object]:
    db_path = get_db_path()
    for suffix in ("", "-wal", "-shm"):
        p = db_path.with_name(db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()

    template = ProjectTemplateLoader().load(template_id)
    project_id, project = await ProjectInitializer.from_template(template)

    gate_config = GateConfig.for_mode("enforce")
    result = await run_project_pipeline(
        project_id=project_id,
        chapter_range=(1, end_chapter),
        mode_id=project.mode_id,
        auto_confirm=True,
        on_failure="isolate",
        gate_config=gate_config,
    )

    t9_metrics = await collect_text_cleanliness_metrics(project_id, 1, end_chapter)
    t9_issue_count = sum(
        m.meta_tag_leak_count + m.duplicate_paragraph_count + m.timeline_conflict_count
        for m in t9_metrics
    )

    word_counts = await _accepted_word_counts(project_id, end_chapter)
    total_words = sum(word_counts.values())
    avg_words = round(total_words / len(word_counts), 0) if word_counts else 0

    return {
        "template_id": template_id,
        "project_id": project_id,
        "completed": result.chapters_completed,
        "failed": result.chapters_failed,
        "status": result.final_status,
        "t9_issue_count": t9_issue_count,
        "word_count_total": total_words,
        "word_count_avg": avg_words,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", nargs="+", default=None, help="要验证的模板 ID 列表")
    parser.add_argument("--end", type=int, default=3, help="结束章节")
    parser.add_argument("--output", default=".tmp/task173_short_window_results.json")
    args = parser.parse_args()

    templates = args.templates or ProjectTemplateLoader().list_templates()
    results = []
    for template_id in templates:
        print(f"\n=== {template_id} ===")
        try:
            summary = asyncio.run(run_for_template(template_id, args.end))
            results.append(summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        except Exception as exc:
            results.append({"template_id": template_id, "error": str(exc)})
            print(f"ERROR: {exc}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()

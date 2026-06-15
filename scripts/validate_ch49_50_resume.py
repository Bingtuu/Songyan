"""Ch49-Ch50 断点续跑验证 — 基于已有 Ch41-Ch48 的 test.db.

Usage:
    cd g:\\vibe\\Songyan && python scripts/validate_ch49_50_resume.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.repository import ChapterVersionRepository
from songyan.workflows.phase2_graph import run_project_pipeline

OUTPUT_DIR = Path("evals/output/validation_ch41_50")
DB_PATH = OUTPUT_DIR / "test.db"


async def _find_resume_point(project_id: str) -> int:
    """查找下一个待生成的章节（从 49 开始）."""
    for ch in range(49, 51):
        versions = await ChapterVersionRepository().list_by_chapter(project_id, ch)
        accepted = [v for v in versions if v.version_type == "accepted"]
        if not accepted:
            return ch
    return 51


async def main() -> None:
    if not DB_PATH.exists():
        print(f"错误：未找到数据库 {DB_PATH}")
        sys.exit(1)

    with patch("songyan.db.connection.get_db_path", return_value=DB_PATH):
        original_url = settings.database_url
        original_mode = settings.checkpointer_mode
        settings.database_url = f"sqlite:///{DB_PATH}"
        settings.checkpointer_mode = "memory"

        try:
            # 在 patch 环境中读取 project_id
            async with get_db() as conn:
                cursor = await conn.execute("SELECT project_id FROM projects LIMIT 1")
                row = await cursor.fetchone()
            if row is None:
                print("错误：数据库中没有任何项目")
                sys.exit(1)

            project_id = row[0]
            resume_at = await _find_resume_point(project_id)
            if resume_at > 50:
                print("Ch49-Ch50 已全部完成，无需续跑")
                return

            print(f"项目 ID: {project_id}")
            print(f"从 Ch{resume_at} 继续...")

            t0 = time.monotonic()
            result = await run_project_pipeline(
                project_id=project_id,
                chapter_range=(resume_at, 50),
                mode_id="webnovel",
                auto_confirm=True,
                on_failure="abort",
            )
            elapsed = time.monotonic() - t0

            report = {
                "validation": f"Ch{resume_at}-Ch50 Real LLM Resume",
                "project_id": project_id,
                "resume_at": resume_at,
                "chapters_completed": result.chapters_completed,
                "chapters_failed": result.chapters_failed,
                "total_duration_sec": round(elapsed, 2),
                "status": "PASS" if not result.chapters_failed else "FAIL",
            }

            report_path = OUTPUT_DIR / "resume_report.json"
            report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
            print(f"\n报告已保存: {report_path}")

        finally:
            settings.database_url = original_url
            settings.checkpointer_mode = original_mode


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""项目基线评估脚本 — 输入 project_id，输出基线指标 JSON."""

from __future__ import annotations

import argparse
import asyncio
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Ensure src is on path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.config import settings
from songyan.db.connection import get_db_path
from songyan.db.context_repo import SummaryRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.db.settlement_repo import (
    ForeshadowingRepository,
    SettingSnapshotRepository,
)
from songyan.models import ChapterVersion, ForeshadowingItem


# ---------------------------------------------------------------------------
# Baseline models
# ---------------------------------------------------------------------------


class ChapterMetric(BaseModel):
    chapter_number: int
    word_count: int
    scene_count: int
    version_count: int
    accepted_version_type: str
    revision_rounds: int = 0


class ConsistencyScanResult(BaseModel):
    orphaned_settings: list[str]  # settings introduced but never referenced again
    unresolved_foreshadowings: list[str]
    forgotten_items: list[str]
    cross_chapter_continuity_score: float  # 0-10


class StyleAnalysisResult(BaseModel):
    repeated_phrases: list[dict[str, Any]]  # [{"phrase": "", "count": 0, "chapters": []}]
    emotion_curve: list[dict[str, Any]]  # per-chapter emotion scores
    avg_paragraph_length: float
    dialogue_ratio: float
    style_score: float  # 0-10


class BaselineReport(BaseModel):
    project_id: str
    project_title: str = ""
    chapter_metrics: list[ChapterMetric]
    consistency_scan: ConsistencyScanResult
    style_analysis: StyleAnalysisResult
    overall_score: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

# Simple Chinese sentiment word lists (baseline heuristic)
_POSITIVE_WORDS = {
    "笑", "喜", "乐", "安", "静", "暖", "光", "希望", "胜利", "成功",
    "轻松", "愉快", "幸福", "满足", "信任", "勇敢", "坚定", "温柔",
}
_NEGATIVE_WORDS = {
    "恐", "惧", "怕", "悲", "痛", "死", "血", "暗", "冷", "绝望",
    "愤怒", "仇恨", "悲伤", "痛苦", "惊恐", "焦虑", "压抑", "窒息",
    "崩溃", "疯狂", "扭曲", "腐烂", "冰冷", "阴冷", "刺骨",
}

# Fatigue / repetitive phrases to detect
_FATIGUE_PATTERNS = [
    (r"呼吸停[滞了]", "呼吸停滞"),
    (r"呼吸[一]?停", "呼吸一停"),
    (r"喃喃自语", "喃喃自语"),
    (r"低声说", "低声说"),
    (r"自言自语", "自言自语"),
    (r"盯着.*看", "盯着看"),
    (r"[僵停]住了", "僵住/停住"),
    (r"心跳[加速漏停]", "心跳异常"),
    (r"然后.*然后", "然后重复"),
    (r"突然.*突然", "突然重复"),
]


def _count_chinese_words(text: str) -> int:
    """粗略中文字数统计."""
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def _count_scenes(text: str) -> int:
    """统计 ### Scene N 标记数."""
    return len(re.findall(r"^###\s*Scene\s+\d+", text, re.MULTILINE | re.IGNORECASE))


def _analyze_emotion(text: str) -> dict[str, float]:
    """基于情感词频的简易情绪分析."""
    text = text.lower()
    pos_count = sum(1 for w in _POSITIVE_WORDS if w in text)
    neg_count = sum(1 for w in _NEGATIVE_WORDS if w in text)
    total = pos_count + neg_count
    if total == 0:
        return {"positive": 0.0, "negative": 0.0, "dominant": "neutral"}
    return {
        "positive": round(pos_count / total, 2),
        "negative": round(neg_count / total, 2),
        "dominant": "negative" if neg_count > pos_count else "positive",
    }


def _detect_repeated_phrases(chapters: list[tuple[int, str]]) -> list[dict[str, Any]]:
    """跨章重复修辞检测."""
    results: list[dict[str, Any]] = []
    for pattern, label in _FATIGUE_PATTERNS:
        total = 0
        chapter_hits: list[int] = []
        for ch_num, text in chapters:
            count = len(re.findall(pattern, text, re.IGNORECASE))
            if count:
                total += count
                chapter_hits.append(ch_num)
        if total >= 2:
            results.append(
                {
                    "phrase": label,
                    "pattern": pattern,
                    "total_count": total,
                    "chapters": chapter_hits,
                }
            )
    # Sort by total count desc
    results.sort(key=lambda x: x["total_count"], reverse=True)
    return results


def _compute_paragraph_stats(chapters: list[tuple[int, str]]) -> tuple[float, float]:
    """计算平均段落长度和对话比例."""
    all_paras: list[str] = []
    dialogue_chars = 0
    total_chars = 0
    for _, text in chapters:
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        all_paras.extend(paras)
        for p in paras:
            chars = _count_chinese_words(p)
            total_chars += chars
            if p.startswith("「") or p.startswith("“") or p.startswith('"'):
                dialogue_chars += chars
    avg_len = (
        sum(_count_chinese_words(p) for p in all_paras) / len(all_paras)
        if all_paras else 0.0
    )
    dialogue_ratio = dialogue_chars / total_chars if total_chars else 0.0
    return round(avg_len, 1), round(dialogue_ratio, 3)


# ---------------------------------------------------------------------------
# Main evaluation logic
# ---------------------------------------------------------------------------


def _load_chapters_from_files(project_id: str) -> tuple[list[ChapterMetric], list[tuple[int, str]], str]:
    """从文件系统加载章节内容（数据库无数据时的 fallback）."""
    project_dir = Path("projects") / project_id / "chapters"
    if not project_dir.exists():
        raise ValueError(f"Project not found in DB or filesystem: {project_id}")

    chapter_files = sorted(project_dir.glob("chapter_*.md"))
    if not chapter_files:
        raise ValueError(f"No chapter files found in {project_dir}")

    chapter_metrics: list[ChapterMetric] = []
    chapters_content: list[tuple[int, str]] = []

    for f in chapter_files:
        match = re.search(r"chapter_(\d+)\.md$", f.name)
        if not match:
            continue
        ch_num = int(match.group(1))
        text = f.read_text(encoding="utf-8")
        word_count = _count_chinese_words(text)
        scene_count = _count_scenes(text)

        # 从文件名推断版本信息（无法从 markdown 文件精确获取）
        chapter_metrics.append(
            ChapterMetric(
                chapter_number=ch_num,
                word_count=word_count,
                scene_count=scene_count,
                version_count=1,
                accepted_version_type="accepted",
                revision_rounds=0,
            )
        )
        chapters_content.append((ch_num, text))

    # 尝试从 README 读取项目标题
    readme_path = Path("projects") / project_id / "README.md"
    title = ""
    if readme_path.exists():
        readme_lines = readme_path.read_text(encoding="utf-8").splitlines()
        if readme_lines and readme_lines[0].startswith("#"):
            title = readme_lines[0].lstrip("# ").strip()

    return chapter_metrics, chapters_content, title


async def evaluate_project(project_id: str) -> BaselineReport:
    """生成项目基线评估报告."""
    project = await ProjectRepository().get(project_id)

    if project is not None:
        # Load all versions and heads from DB
        version_repo = ChapterVersionRepository()

        # Find all chapter numbers with data
        db_path = get_db_path()
        import aiosqlite

        async with aiosqlite.connect(str(db_path)) as conn:
            cursor = await conn.execute(
                "SELECT DISTINCT chapter_number FROM chapter_versions "
                "WHERE project_id = ? ORDER BY chapter_number",
                (project_id,),
            )
            chapter_numbers = [row[0] for row in await cursor.fetchall()]

        if not chapter_numbers:
            raise ValueError(f"No chapters found for project: {project_id}")

        chapter_metrics: list[ChapterMetric] = []
        chapters_content: list[tuple[int, str]] = []

        for ch_num in chapter_numbers:
            versions = await version_repo.list_by_chapter(project_id, ch_num)
            accepted = [v for v in versions if v.version_type == "accepted"]
            best = accepted[-1] if accepted else versions[-1] if versions else None

            if best is None:
                continue

            revision_rounds = max(0, len(versions) - 1)
            scene_count = len(best.scenes) if best.scenes else _count_scenes(best.content)

            chapter_metrics.append(
                ChapterMetric(
                    chapter_number=ch_num,
                    word_count=best.word_count or _count_chinese_words(best.content),
                    scene_count=scene_count,
                    version_count=len(versions),
                    accepted_version_type=best.version_type,
                    revision_rounds=revision_rounds,
                )
            )
            chapters_content.append((ch_num, best.content))

        # Consistency scan from DB
        settings_repo = SettingSnapshotRepository()
        foreshadowing_repo = ForeshadowingRepository()

        all_settings = await settings_repo.list_by_project(project_id)
        all_foreshadowings = await foreshadowing_repo.list_by_project(project_id)

        # Orphaned settings: introduced but never mentioned in later chapters
        setting_keys = {s.setting_key for s in all_settings if s.setting_key}
        orphaned: list[str] = []
        for key in setting_keys:
            mentions = sum(1 for _, text in chapters_content if key in text)
            if mentions <= 1:
                orphaned.append(key)

        unresolved = [f.foreshadowing_id for f in all_foreshadowings if f.status == "planted"]
        title = project.title or ""
    else:
        # Fallback: load from filesystem
        chapter_metrics, chapters_content, title = _load_chapters_from_files(project_id)
        orphaned = []
        unresolved = []

    # Cross-chapter continuity: simple heuristic based on revision rounds and orphaned items
    continuity_score = 10.0
    continuity_score -= len(orphaned) * 0.5
    continuity_score -= len(unresolved) * 0.3
    for cm in chapter_metrics:
        if cm.revision_rounds > 3:
            continuity_score -= 0.2 * (cm.revision_rounds - 3)
    continuity_score = max(0.0, min(10.0, continuity_score))

    consistency_scan = ConsistencyScanResult(
        orphaned_settings=orphaned,
        unresolved_foreshadowings=unresolved,
        forgotten_items=orphaned + unresolved,
        cross_chapter_continuity_score=round(continuity_score, 2),
    )

    # Style analysis
    repeated_phrases = _detect_repeated_phrases(chapters_content)
    emotion_curve = [
        {
            "chapter_number": ch_num,
            **_analyze_emotion(text),
        }
        for ch_num, text in chapters_content
    ]
    avg_para_len, dialogue_ratio = _compute_paragraph_stats(chapters_content)

    # Style score: penalize repeated phrases and very low dialogue ratio
    style_score = 8.0
    style_score -= len(repeated_phrases) * 0.3
    style_score -= sum(r["total_count"] for r in repeated_phrases) * 0.1
    if dialogue_ratio < 0.1:
        style_score -= 1.0
    style_score = max(0.0, min(10.0, style_score))

    style_analysis = StyleAnalysisResult(
        repeated_phrases=repeated_phrases,
        emotion_curve=emotion_curve,
        avg_paragraph_length=avg_para_len,
        dialogue_ratio=dialogue_ratio,
        style_score=round(style_score, 2),
    )

    # Overall score: weighted average
    total_words = sum(cm.word_count for cm in chapter_metrics)
    word_consistency = 1.0 - (
        sum(abs(cm.word_count - 3500) for cm in chapter_metrics)
        / (len(chapter_metrics) * 3500)
    )
    word_consistency = max(0.0, min(1.0, word_consistency))

    overall = (
        continuity_score * 0.35
        + style_score * 0.35
        + word_consistency * 10 * 0.15
        + (10 - len(orphaned) * 0.5 - len(unresolved) * 0.3) * 0.15
    )
    overall = max(0.0, min(10.0, overall))

    return BaselineReport(
        project_id=project_id,
        project_title=title,
        chapter_metrics=chapter_metrics,
        consistency_scan=consistency_scan,
        style_analysis=style_analysis,
        overall_score=round(overall, 2),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Songyan project baseline evaluation")
    parser.add_argument("--project-id", required=True, help="Project ID to evaluate")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    args = parser.parse_args()

    async def _run() -> None:
        report = await evaluate_project(args.project_id)
        report_json = report.model_dump_json(indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(report_json, encoding="utf-8")
            print(f"Report written to {args.output}")
        else:
            print(report_json)

    asyncio.run(_run())


if __name__ == "__main__":
    main()

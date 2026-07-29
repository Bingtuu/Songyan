"""Task 196: 优秀度样本集分层抽样与标注模型.

离线 report/observe 基础设施：不进入生成链路，不影响 CED/五门/T9 口径。
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

SEGMENT_SIZE = 25
SAMPLES_PER_GENRE = 30
DEFAULT_SEED = 196


class ExcellenceSamplingError(Exception):
    """Task 196 抽样/标注错误."""


@dataclass(frozen=True)
class SampledChapter:
    genre: str
    chapter_number: int
    version_id: str
    segment: int  # 1-based，25 章一个弧段

    def to_dict(self) -> dict:
        return {
            "genre": self.genre,
            "chapter": self.chapter_number,
            "version_id": self.version_id,
            "segment": self.segment,
        }


class AnnotationScores(BaseModel):
    homogeneity: int = Field(ge=1, le=5)
    tension: int = Field(ge=1, le=5)
    ai_tone: int = Field(ge=1, le=5)
    overall: int = Field(ge=1, le=5)


class AnnotationRecord(BaseModel):
    genre: str
    chapter: int = Field(ge=1)
    version_id: str
    sample_layer: Literal["anchor", "prelabel", "spotcheck"]
    scores: AnnotationScores
    rationale: str = ""
    evidence_quotes: list[str] = Field(default_factory=list)
    annotator: Literal["agent-deep-read", "llm-prelabel", "human-review"]
    disagreement: str | None = None


def stratified_sample(
    chapters: list[SampledChapter],
    *,
    per_genre: int = SAMPLES_PER_GENRE,
    seed: int = DEFAULT_SEED,
) -> list[SampledChapter]:
    """按 25 章弧段分层抽样：每段配额 = 基数 + 前 rem 段各 +1，段内固定 seed 随机."""
    if not chapters:
        raise ExcellenceSamplingError("empty chapter list")
    segments: dict[int, list[SampledChapter]] = {}
    for c in chapters:
        segments.setdefault(c.segment, []).append(c)
    seg_ids = sorted(segments)
    base, rem = divmod(per_genre, len(seg_ids))
    rng = random.Random(seed)
    picked: list[SampledChapter] = []
    for i, seg_id in enumerate(seg_ids):
        quota = base + (1 if i < rem else 0)
        pool = segments[seg_id]
        picked.extend(rng.sample(pool, min(quota, len(pool))))
    return sorted(picked, key=lambda c: c.chapter_number)


def load_accepted_chapters(
    conn: sqlite3.Connection,
    project_id: str,
    genre: str,
) -> list[SampledChapter]:
    """按 five_gate_acceptance.py:302-318 的 JOIN 口径读 accepted heads."""
    rows = conn.execute(
        """SELECT ch.chapter_number, ch.accepted_version_id
           FROM chapter_heads ch
           JOIN chapter_versions cv ON cv.version_id = ch.accepted_version_id
           WHERE ch.project_id = ? AND ch.accepted_version_id IS NOT NULL
           ORDER BY ch.chapter_number""",
        (project_id,),
    ).fetchall()
    if not rows:
        raise ExcellenceSamplingError(f"no accepted chapters for project {project_id}")
    return [
        SampledChapter(
            genre=genre,
            chapter_number=r[0],
            version_id=r[1],
            segment=(r[0] - 1) // SEGMENT_SIZE + 1,
        )
        for r in rows
    ]


def load_chapter_content(conn: sqlite3.Connection, version_id: str) -> str:
    row = conn.execute(
        "SELECT content FROM chapter_versions WHERE version_id = ?", (version_id,)
    ).fetchone()
    if row is None:
        raise ExcellenceSamplingError(f"version {version_id} not found")
    return row[0]

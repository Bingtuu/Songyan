"""Async repositories for creative brief and review data."""

from __future__ import annotations

from sqlite3 import Row
from typing import Any

import structlog

from songyan.db.connection import get_db
from songyan.models import (
    ChapterGoal,
    CreativeBrief,
    EmotionArcItem,
    LiteraryAuditResult,
    LiteraryObservation,
    LLMAuditResult,
    MergedReviewReport,
    PunchPoint,
    ReviewIssue,
    RuleAuditResult,
    Tension,
)
from songyan.utils.json_helpers import from_json as _from_json
from songyan.utils.json_helpers import model_json as _model_json
from songyan.utils.json_helpers import to_json as _to_json

logger = structlog.get_logger(__name__)


class CreativeBriefRepository:
    """Repository for CreativeDirector output."""

    async def create(
        self,
        brief: CreativeBrief,
        brief_id: str,
        project_id: str,
        chapter_number: int,
    ) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO creative_briefs (
                    brief_id, project_id, chapter_number, mode_id, creative_intent,
                    required_tensions, forbidden_patterns, allowed_fissures,
                    style_constraints, reader_contract, polyphony_notes, chapter_goal,
                    punch_points, emotion_arc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    brief_id,
                    project_id,
                    chapter_number,
                    brief.mode_id,
                    brief.creative_intent,
                    _model_json(brief.required_tensions),
                    _to_json(brief.forbidden_patterns),
                    _to_json(brief.allowed_fissures),
                    _to_json(brief.style_constraints),
                    brief.reader_contract,
                    _to_json(brief.polyphony_notes),
                    _model_json(brief.chapter_goal),
                    _model_json(brief.punch_points),
                    _model_json(brief.emotion_arc),
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="creative_briefs",
            operation="insert",
            brief_id=brief_id,
        )

    async def get(self, brief_id: str) -> CreativeBrief | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM creative_briefs WHERE brief_id = ?",
                (brief_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        goal_data = _from_json(row["chapter_goal"], {})
        chapter_goal = (
            ChapterGoal.model_validate(goal_data)
            if goal_data and "chapter_number" in goal_data
            else None
        )
        return CreativeBrief(
            mode_id=row["mode_id"],
            chapter_goal=chapter_goal,
            creative_intent=row["creative_intent"],
            required_tensions=[
                Tension.model_validate(item) for item in _from_json(row["required_tensions"], [])
            ],
            forbidden_patterns=_from_json(row["forbidden_patterns"], []),
            allowed_fissures=_from_json(row["allowed_fissures"], []),
            style_constraints=_from_json(row["style_constraints"], []),
            reader_contract=row["reader_contract"],
            polyphony_notes=_from_json(row["polyphony_notes"], []),
            punch_points=[
                PunchPoint.model_validate(item) for item in _from_json(row["punch_points"], [])
            ],
            emotion_arc=[
                EmotionArcItem.model_validate(item) for item in _from_json(row["emotion_arc"], [])
            ],
        )


class ReviewReportRepository:
    """Repository for merged review reports."""

    async def create(
        self, report: MergedReviewReport, report_id: str, audit_type: str = "merged"
    ) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO review_reports (
                    report_id, chapter_version_id, audit_type, rule_audit_result,
                    llm_audit_result, issues, overall_score, ai_tell_count,
                    fatigue_word_count, has_opening_hook, has_ending_hook,
                    dimension_scores, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    report_id,
                    report.chapter_version_id,
                    audit_type,
                    _model_json(report.rule_audit) if report.rule_audit else "{}",
                    _model_json(report.llm_audit) if report.llm_audit else "{}",
                    _model_json(report.issues),
                    report.overall_score,
                    report.ai_tell_count,
                    report.fatigue_word_count,
                    int(report.has_opening_hook),
                    int(report.has_ending_hook),
                    _to_json(report.dimension_scores),
                    report.summary,
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="review_reports",
            operation="insert",
            report_id=report_id,
        )

    async def get_by_version(
        self, chapter_version_id: str, audit_type: str = "merged"
    ) -> MergedReviewReport | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM review_reports
                WHERE chapter_version_id = ? AND audit_type = ?
                ORDER BY created_at DESC, report_id DESC
                LIMIT 1""",
                (chapter_version_id, audit_type),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        rule_data = _from_json(row["rule_audit_result"], {})
        llm_data = _from_json(row["llm_audit_result"], {})
        return MergedReviewReport(
            chapter_version_id=row["chapter_version_id"],
            rule_audit=RuleAuditResult.model_validate(rule_data) if rule_data else None,
            llm_audit=LLMAuditResult.model_validate(llm_data) if llm_data else None,
            issues=[ReviewIssue.model_validate(item) for item in _from_json(row["issues"], [])],
            overall_score=row["overall_score"],
            ai_tell_count=row["ai_tell_count"],
            fatigue_word_count=row["fatigue_word_count"],
            has_opening_hook=bool(row["has_opening_hook"]),
            has_ending_hook=bool(row["has_ending_hook"]),
            dimension_scores=_from_json(row["dimension_scores"], {}),
            summary=row["summary"],
        )


class LiteraryObservationRepository:
    """Repository for literary audit observations."""

    async def create(
        self,
        result: LiteraryAuditResult,
        observation_id: str,
        version_id: str,
    ) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO literary_observations (
                    observation_id, version_id, auditor_id, observations,
                    literary_quality_score, character_autonomy_score,
                    conceptual_grounding_score, fissure_preservation_score,
                    summary, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    observation_id,
                    version_id,
                    result.auditor_id,
                    _model_json(result.observations),
                    result.literary_quality_score,
                    result.character_autonomy_score,
                    result.conceptual_grounding_score,
                    result.fissure_preservation_score,
                    result.summary,
                    result.duration_ms,
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="literary_observations",
            operation="insert",
            observation_id=observation_id,
        )

    async def get_latest_id_by_version(self, version_id: str) -> str | None:
        """Return latest literary observation id for a chapter version."""
        async with get_db() as conn:
            cursor = await conn.execute(
                """SELECT observation_id FROM literary_observations
                WHERE version_id = ?
                ORDER BY created_at DESC, observation_id DESC
                LIMIT 1""",
                (version_id,),
            )
            row = await cursor.fetchone()
        return row[0] if row else None

    async def get_by_version(self, version_id: str) -> LiteraryAuditResult | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM literary_observations
                WHERE version_id = ?
                ORDER BY created_at DESC, observation_id DESC
                LIMIT 1""",
                (version_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return LiteraryAuditResult(
            auditor_id=row["auditor_id"],
            observations=[
                LiteraryObservation.model_validate(item)
                for item in _from_json(row["observations"], [])
            ],
            literary_quality_score=row["literary_quality_score"],
            character_autonomy_score=row["character_autonomy_score"],
            conceptual_grounding_score=row["conceptual_grounding_score"],
            fissure_preservation_score=row["fissure_preservation_score"],
            summary=row["summary"],
            duration_ms=row["duration_ms"],
        )

    async def list_scores_by_chapter_range(
        self, project_id: str, start: int, end: int
    ) -> list[dict]:
        """按章回读文学四维度分数（JOIN chapter_versions，每章取最新一条 observation）.

        literary_observations 无 chapter_number，经 version_id → chapter_versions 关联；
        每章可能多版本/多次审查，取 created_at 最新的一条。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT cv.chapter_number AS chapter,
                          lo.literary_quality_score,
                          lo.character_autonomy_score,
                          lo.conceptual_grounding_score,
                          lo.fissure_preservation_score
                   FROM literary_observations lo
                   JOIN chapter_versions cv ON lo.version_id = cv.version_id
                   WHERE cv.project_id = ?
                     AND cv.chapter_number BETWEEN ? AND ?
                   ORDER BY cv.chapter_number, lo.created_at DESC, lo.observation_id DESC""",
                (project_id, start, end),
            )
            rows = await cursor.fetchall()
        seen: set[int] = set()
        result: list[dict] = []
        for row in rows:
            chapter = row["chapter"]
            if chapter in seen:
                continue
            seen.add(chapter)
            result.append(dict(row))
        return result

    async def list_observations_by_chapter_range(
        self, project_id: str, start: int, end: int
    ) -> list[dict[str, Any]]:
        """按章回读最新文学诊断明细（供 166a 风格债转规划约束）."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT cv.chapter_number AS chapter,
                          lo.observation_id,
                          lo.observations,
                          lo.summary,
                          lo.literary_quality_score,
                          lo.character_autonomy_score,
                          lo.conceptual_grounding_score,
                          lo.fissure_preservation_score
                   FROM literary_observations lo
                   JOIN chapter_versions cv ON lo.version_id = cv.version_id
                   WHERE cv.project_id = ?
                     AND cv.chapter_number BETWEEN ? AND ?
                   ORDER BY cv.chapter_number, lo.created_at DESC, lo.observation_id DESC""",
                (project_id, start, end),
            )
            rows = await cursor.fetchall()
        seen: set[int] = set()
        result: list[dict[str, Any]] = []
        for row in rows:
            chapter = int(row["chapter"])
            if chapter in seen:
                continue
            seen.add(chapter)
            result.append(
                {
                    "chapter": chapter,
                    "observation_id": row["observation_id"],
                    "observations": _from_json(row["observations"], []),
                    "summary": row["summary"] or "",
                    "literary_quality_score": row["literary_quality_score"],
                    "character_autonomy_score": row["character_autonomy_score"],
                    "conceptual_grounding_score": row["conceptual_grounding_score"],
                    "fissure_preservation_score": row["fissure_preservation_score"],
                }
            )
        return result

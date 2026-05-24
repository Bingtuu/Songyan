"""Async repositories for creative brief and review data."""

from __future__ import annotations

from sqlite3 import Row

import structlog

from songyan.db.connection import get_db
from songyan.db.repository import _from_json, _model_json, _to_json
from songyan.models import (
    ChapterGoal,
    CreativeBrief,
    LiteraryAuditResult,
    LiteraryObservation,
    LLMAuditResult,
    MergedReviewReport,
    ReviewIssue,
    RuleAuditResult,
    Tension,
)

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
                    style_constraints, reader_contract, polyphony_notes, chapter_goal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        return CreativeBrief(
            mode_id=row["mode_id"],
            chapter_goal=ChapterGoal.model_validate(_from_json(row["chapter_goal"], {})),
            creative_intent=row["creative_intent"],
            required_tensions=[
                Tension.model_validate(item) for item in _from_json(row["required_tensions"], [])
            ],
            forbidden_patterns=_from_json(row["forbidden_patterns"], []),
            allowed_fissures=_from_json(row["allowed_fissures"], []),
            style_constraints=_from_json(row["style_constraints"], []),
            reader_contract=row["reader_contract"],
            polyphony_notes=_from_json(row["polyphony_notes"], []),
        )


class ReviewReportRepository:
    """Repository for merged review reports."""

    async def create(self, report: MergedReviewReport, report_id: str) -> None:
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
                    "merged",
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

    async def get_by_version(self, chapter_version_id: str) -> MergedReviewReport | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM review_reports
                WHERE chapter_version_id = ?
                ORDER BY created_at DESC, report_id DESC
                LIMIT 1""",
                (chapter_version_id,),
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

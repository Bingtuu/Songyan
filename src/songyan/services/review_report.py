"""M4 步 4 review 只读共审聚合（tech-m4 §4.4 / B8 / B11）。

被审正文口径（M1 决策）：``head.current_version_id`` 工作稿——W2 共审针对未 accept
的工作稿，与 ``check`` 的 accepted 口径**显式分叉**（check 审已确认稿，review 审
待确认稿；理由见 tasks/241 评审 M1）。

零写库硬约束（B8）：全程只读；**不调用** ``merge_reviews``（其写 ``review_reports``
的副作用违反本决策，合并只在内存呈现）；variant 备注**直读**
``ChapterVariantRepository().list_for_chapter``——禁用服务入口 ``list_variant_rows``
（它会 ``refresh_stale_vs_canon`` 写库）；gate 现算（``run_plan_fact_gate`` 只读，
入参正文 = 工作稿；typed-attribute extracts 腿恒空，同 ``check`` 生产路径不传
extracts）。
"""

from __future__ import annotations

from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.db.review_repo import LiteraryObservationRepository
from songyan.models.human_mark import HumanMark
from songyan.models.review import LLMAuditResult, RuleAuditResult
from songyan.plan_checks.gate import PlanFactGateReport, run_plan_fact_gate
from songyan.plan_checks.proper_noun_check import ProperNounHit, check_proper_nouns
from songyan.plan_checks.repetition_check import RepetitionHit, check_repetition
from songyan.workflows._helpers import load_latest_audits

logger = structlog.get_logger(__name__)

# 零写库断言清单（tasks/241 切片 1）：plan_* 五表 + 八张业务表。
ZERO_WRITE_TABLES: tuple[str, ...] = (
    "plan_entities",
    "plan_attributes",
    "plan_events",
    "plan_clues",
    "plan_time_anchors",
    "review_reports",
    "literary_observations",
    "chapter_heads",
    "chapter_versions",
    "chapter_variants",
    "context_snapshots",
    "human_marks",
)

_NO_WORKDRAFT = "无工作稿（head.current_version_id 为空）：gate / 复读 / 专名分区跳过"
_NO_PREVIOUS_ACCEPTED = "上一章无 accepted 正文，跨章复读腿跳过"

ReviewSeverity = Literal["hard", "warning", "info"]


class AuditSnapshot(BaseModel):
    """一章某一版本的最新三审结果（rule + llm，均可缺）。"""

    version_id: str
    version_number: int
    version_type: str
    rule: RuleAuditResult | None = None
    llm: LLMAuditResult | None = None


class VariantNote(BaseModel):
    """variant 备注（只读直读 chapter_variants，不触发 stale refresh）。"""

    variant_id: str
    slot_index: int
    status: str
    stale_vs_canon: int
    cost_cny_estimate: float


class ReviewFinding(BaseModel):
    """内存合并后的单条呈现项：按严重度分组、带证据引用。"""

    severity: ReviewSeverity
    source: str
    message: str
    evidence: str = ""
    location: str = ""


class ChapterReviewReport(BaseModel):
    """一章的只读共审报告（七源分区 + 内存合并 findings）。"""

    project_id: str
    chapter: int
    workdraft_version_id: str | None = None
    gate: PlanFactGateReport | None = None
    gate_note: str = ""
    audits: list[AuditSnapshot] = Field(default_factory=list)
    literary: list[dict[str, Any]] = Field(default_factory=list)
    repetition_hits: list[RepetitionHit] = Field(default_factory=list)
    repetition_note: str = ""
    proper_noun_hits: list[ProperNounHit] = Field(default_factory=list)
    variant_notes: list[VariantNote] = Field(default_factory=list)
    human_marks: list[HumanMark] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)


async def list_chapter_universe(project_id: str) -> list[int]:
    """章宇宙 = chapter_heads 行（B1 口径）；返回升序章号。只读。"""
    heads = await ChapterHeadRepository().list_by_project(project_id)
    return sorted(head.chapter_number for head in heads)


async def build_chapter_review(project_id: str, chapter: int) -> ChapterReviewReport:
    """聚合一章的七源输入（B8 输入并集），全程只读、内存合并呈现。"""
    if chapter < 1:
        raise ValueError("chapter must be >= 1")

    head = await ChapterHeadRepository().get(project_id, chapter)
    workdraft_version_id = head.current_version_id if head else None
    workdraft_text: str | None = None
    if workdraft_version_id:
        version = await ChapterVersionRepository().get(workdraft_version_id)
        if version is not None and (version.content or "").strip():
            workdraft_text = version.content

    gate: PlanFactGateReport | None = None
    gate_note = ""
    repetition_hits: list[RepetitionHit] = []
    repetition_note = ""
    proper_noun_hits: list[ProperNounHit] = []
    if workdraft_text is None:
        gate_note = _NO_WORKDRAFT
        repetition_note = _NO_WORKDRAFT
    else:
        # ① gate 现算：入参正文 = 工作稿；不传 extracts（typed 腿恒空，同 check 生产路径）。
        gate = await run_plan_fact_gate(project_id, chapter, workdraft_text)

        # ④ 复读启发式（现算）；跨章腿与上一章 accepted 比对。
        previous_text = await _previous_accepted_text(project_id, chapter)
        if previous_text is None:
            repetition_note = _NO_PREVIOUS_ACCEPTED
        repetition_hits = check_repetition(
            workdraft_text,
            chapter=chapter,
            previous_accepted_text=previous_text,
        )

        # ⑤ 专名启发式（现算）；已登记集合 = 三处并集。
        registered = await _load_registered_names(project_id)
        proper_noun_hits = check_proper_nouns(
            workdraft_text, chapter=chapter, registered=registered
        )

    # ② 三审：遍历该章全部版本取每版最新（审计跑在生成时 draft 版上，
    #    只看 accepted 副本会恒空）。
    audits: list[AuditSnapshot] = []
    versions = await ChapterVersionRepository().list_by_chapter(
        project_id, chapter, include_abandoned=True
    )
    for version in versions:
        rule, llm = await load_latest_audits(version.version_id)
        if rule is None and llm is None:
            continue
        audits.append(
            AuditSnapshot(
                version_id=version.version_id,
                version_number=version.version_number,
                version_type=version.version_type,
                rule=rule,
                llm=llm,
            )
        )

    # ③ literary_observations：按章回读（同受全版本口径影响，按章范围读即可）。
    literary = await LiteraryObservationRepository().list_observations_by_chapter_range(
        project_id, chapter, chapter
    )

    # ⑥ variant 备注：直读 repo，禁用 list_variant_rows（会 refresh 写库）。
    variants = await ChapterVariantRepository().list_for_chapter(project_id, chapter)
    variant_notes = [
        VariantNote(
            variant_id=variant.variant_id,
            slot_index=variant.slot_index,
            status=str(variant.status),
            stale_vs_canon=int(variant.stale_vs_canon),
            cost_cny_estimate=float(variant.cost_cny_estimate),
        )
        for variant in variants
    ]

    # ⑦ 人的 mark：纯读，过滤 created_at_chapter ≤ 被审章。
    human_marks = await HumanMarkRepository().list_by_chapter_range(project_id, 1, chapter)

    report = ChapterReviewReport(
        project_id=project_id,
        chapter=chapter,
        workdraft_version_id=workdraft_version_id if workdraft_text is not None else None,
        gate=gate,
        gate_note=gate_note,
        audits=audits,
        literary=literary,
        repetition_hits=repetition_hits,
        repetition_note=repetition_note,
        proper_noun_hits=proper_noun_hits,
        variant_notes=variant_notes,
        human_marks=human_marks,
    )
    report.findings = collect_findings(report)
    logger.info(
        "review_report.built",
        project_id=project_id,
        chapter=chapter,
        findings=len(report.findings),
        zero_write=True,
    )
    return report


def collect_findings(report: ChapterReviewReport) -> list[ReviewFinding]:
    """内存合并七源为呈现 findings（不按此写库；严重度分组用）。"""
    findings: list[ReviewFinding] = []

    if report.gate is not None:
        gate = report.gate
        for mention in gate.missing_mentions:
            terms = "、".join(mention.missing_terms) or mention.label
            findings.append(
                ReviewFinding(
                    severity="hard",
                    source="gate",
                    message=f"必须提及缺失 `{mention.point_id}`（{mention.label}）：{terms}",
                    evidence=terms,
                )
            )
        for mismatch in gate.attribute_mismatches:
            findings.append(
                ReviewFinding(
                    severity="hard",
                    source="gate",
                    message=(
                        f"属性不一致 实体 `{mismatch.entity_id}` 键 `{mismatch.key}`："
                        f"圣经值「{mismatch.approved_value}」≠ 正文侧值「{mismatch.extract_value}」"
                    ),
                    evidence=str(mismatch.extract_value),
                )
            )
        for verdict in gate.claim_verdicts:
            if verdict.status == "supported":
                continue
            findings.append(
                ReviewFinding(
                    severity="hard",
                    source="gate",
                    message=f"主张 `{verdict.claim_id}`：{verdict.status} — {verdict.text}",
                    evidence=verdict.text,
                )
            )

    for snapshot in report.audits:
        if snapshot.llm is not None:
            for issue in snapshot.llm.issues:
                severity: ReviewSeverity = (
                    "hard" if issue.severity in ("critical", "major")
                    else "warning" if issue.severity == "minor"
                    else "info"
                )
                findings.append(
                    ReviewFinding(
                        severity=severity,
                        source="audit",
                        message=f"[{issue.category}] {issue.issue_description}",
                        evidence=issue.evidence_quote,
                        location=issue.evidence_location,
                    )
                )

    for row in report.literary:
        for observation in row.get("observations", []):
            severity = "hard" if observation.get("severity") == "critical" else "info"
            findings.append(
                ReviewFinding(
                    severity=severity,
                    source="literary",
                    message=f"[{observation.get('observation_type')}] "
                    f"{observation.get('description')}",
                    evidence=str(observation.get("evidence_quote") or ""),
                )
            )

    for repeat in report.repetition_hits:
        findings.append(
            ReviewFinding(
                severity="warning",
                source="repetition",
                message=f"复读（{repeat.kind}）：{repeat.detail}",
                evidence=repeat.quote,
                location=repeat.location,
            )
        )

    for noun in report.proper_noun_hits:
        findings.append(
            ReviewFinding(
                severity="info",
                source="proper_noun",
                message=f"{noun.detail}：{noun.name}",
                evidence=noun.name,
                location=noun.location,
            )
        )

    for note in report.variant_notes:
        if note.stale_vs_canon == 1:
            findings.append(
                ReviewFinding(
                    severity="warning",
                    source="variant",
                    message=f"variant 槽 {note.slot_index}（{note.status}）已 stale_vs_canon",
                    evidence=note.variant_id,
                )
            )

    for mark in report.human_marks:
        findings.append(
            ReviewFinding(
                severity="info",
                source="human_mark",
                message=f"人的 mark [{mark.mark_type}] {mark.target_key}：{mark.note}",
                evidence=mark.target_key,
            )
        )

    order = {"hard": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda item: order[item.severity])
    return findings


async def _previous_accepted_text(project_id: str, chapter: int) -> str | None:
    """上一章（章号-1）的 accepted 正文；无 head / 无 accepted / 正文空 → None。"""
    if chapter <= 1:
        return None
    previous_head = await ChapterHeadRepository().get(project_id, chapter - 1)
    if previous_head is None or previous_head.accepted_version_id is None:
        return None
    version = await ChapterVersionRepository().get(previous_head.accepted_version_id)
    if version is None or not (version.content or "").strip():
        return None
    return version.content


async def _load_registered_names(project_id: str) -> set[str]:
    """已登记专名集合 = canon approved aliases ∪ 主角名 ∪ characters protagonist 名。"""
    names: set[str] = set()
    for entity in await PlanFactRepository().list_canon_entities(project_id):
        names.add(entity.entity_id)
        names.update(entity.aliases)
    project = await ProjectRepository().get(project_id)
    if project is not None and project.protagonist_name:
        names.add(project.protagonist_name)
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT name FROM characters WHERE project_id = ? AND role_type = 'protagonist'",
            (project_id,),
        )
        rows = await cursor.fetchall()
    names.update(str(row[0]) for row in rows if row and row[0])
    return names

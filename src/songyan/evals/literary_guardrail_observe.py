"""171w-c observe checks for literary guardrails in accepted text."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, cast

from songyan.db.connection import get_db
from songyan.models import ReviewCategory, ReviewIssue
from songyan.models.creative_mode import CreativeBrief

_ACTIVE_VERBS: tuple[str, ...] = (
    "主动",
    "选择",
    "决定",
    "拒绝",
    "切断",
    "关闭",
    "启动",
    "改变",
    "转向",
    "绕开",
    "推开",
    "按下",
    "命令",
    "要求",
    "牺牲",
    "放弃",
    "手动",
)
_PASSIVE_ONLY_PATTERNS: tuple[str, ...] = ("继续破解", "继续推进", "继续承受", "等待协议")
_COST_KEYWORDS: tuple[str, ...] = ("代价", "暴露", "牺牲", "失去", "风险", "受伤", "损耗", "不可逆")
_SUPPORTING_ACTION_KEYWORDS: tuple[str, ...] = (
    "拒绝",
    "坚持",
    "隐瞒",
    "阻止",
    "拦",
    "改变",
    "拖延",
    "带",
    "离开",
    "抢",
    "关闭",
    "切断",
    "转向",
    "要求",
    "迫使",
)
_CONSEQUENCE_KEYWORDS: tuple[str, ...] = (
    "延迟",
    "改变路线",
    "路线变化",
    "代价",
    "误判",
    "压力",
    "暴露",
    "失去",
    "迫使",
)


@dataclass(slots=True)
class SupportingGoalObservation:
    character: str = ""
    goal: str = ""
    character_present: bool = False
    action_evidence: str = ""
    consequence_evidence: str = ""
    passed: bool = False
    skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "character": self.character,
            "goal": self.goal,
            "character_present": self.character_present,
            "action_evidence": self.action_evidence,
            "consequence_evidence": self.consequence_evidence,
            "passed": self.passed,
            "skipped": self.skipped,
        }


@dataclass(slots=True)
class ActiveChoiceObservation:
    protagonist_name: str
    active_choice_evidence: str = ""
    cost_evidence: str = ""
    passive_only: bool = False
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "protagonist_name": self.protagonist_name,
            "active_choice_evidence": self.active_choice_evidence,
            "cost_evidence": self.cost_evidence,
            "passive_only": self.passive_only,
            "passed": self.passed,
        }


@dataclass(slots=True)
class ConceptBudgetObservation:
    max_new_core_concepts: int = 1
    raw_new_settings_count: int = 0
    core_concept_count: int = 0
    grounded_new_concept_count: int = 0
    ungrounded_new_concept_count: int = 0
    concept_groups: dict[str, list[str]] = field(default_factory=dict)
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_new_core_concepts": self.max_new_core_concepts,
            "raw_new_settings_count": self.raw_new_settings_count,
            "core_concept_count": self.core_concept_count,
            "grounded_new_concept_count": self.grounded_new_concept_count,
            "ungrounded_new_concept_count": self.ungrounded_new_concept_count,
            "concept_groups": self.concept_groups,
            "passed": self.passed,
        }


@dataclass(slots=True)
class LiteraryGuardrailObservationRow:
    chapter_number: int
    accepted_version_id: str | None = None
    supporting_goal: SupportingGoalObservation = field(
        default_factory=SupportingGoalObservation
    )
    active_choice: ActiveChoiceObservation | None = None
    concept_budget: ConceptBudgetObservation = field(
        default_factory=ConceptBudgetObservation
    )

    @property
    def passed(self) -> bool:
        active_passed = self.active_choice.passed if self.active_choice else False
        return (
            self.supporting_goal.passed
            and active_passed
            and self.concept_budget.passed
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "accepted_version_id": self.accepted_version_id,
            "supporting_goal": self.supporting_goal.to_dict(),
            "active_choice": self.active_choice.to_dict() if self.active_choice else None,
            "concept_budget": self.concept_budget.to_dict(),
            "passed": self.passed,
        }


def _loads_json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _split_sentences(text: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"(?<=[。！？!?])\s*|\n+", text)
        if item.strip()
    ]


def _first_sentence_with(
    sentences: list[str],
    required: str,
    keywords: tuple[str, ...],
) -> str:
    for sentence in sentences:
        if required in sentence and any(keyword in sentence for keyword in keywords):
            return sentence
    return ""


def observe_supporting_character_goal(
    content: str,
    supporting_goal: dict[str, Any] | None,
) -> SupportingGoalObservation:
    """Observe whether a supporting-character goal is actually carried by text."""
    if not supporting_goal:
        return SupportingGoalObservation(skipped=True, passed=True)
    character = str(supporting_goal.get("character") or "").strip()
    goal = str(supporting_goal.get("goal") or "").strip()
    if not character:
        return SupportingGoalObservation(goal=goal, skipped=True, passed=True)

    sentences = _split_sentences(content)
    action_evidence = _first_sentence_with(sentences, character, _SUPPORTING_ACTION_KEYWORDS)
    consequence_evidence = ""
    if action_evidence:
        idx = sentences.index(action_evidence)
        window = "。".join(sentences[max(0, idx - 1) : idx + 2])
        if any(keyword in window for keyword in _CONSEQUENCE_KEYWORDS):
            consequence_evidence = window

    character_present = character in content
    return SupportingGoalObservation(
        character=character,
        goal=goal,
        character_present=character_present,
        action_evidence=action_evidence,
        consequence_evidence=consequence_evidence,
        passed=bool(character_present and action_evidence and consequence_evidence),
    )


def observe_active_choice(
    content: str,
    protagonist_name: str = "林渊",
) -> ActiveChoiceObservation:
    """Observe whether the protagonist makes a concrete active choice."""
    sentences = _split_sentences(content)
    active_evidence = _first_sentence_with(sentences, protagonist_name, _ACTIVE_VERBS)
    cost_evidence = ""
    if active_evidence:
        idx = sentences.index(active_evidence)
        window = "。".join(sentences[max(0, idx - 1) : idx + 2])
        if any(keyword in window for keyword in _COST_KEYWORDS):
            cost_evidence = window
    passive_only = (
        any(pattern in content for pattern in _PASSIVE_ONLY_PATTERNS)
        and not active_evidence
    )
    return ActiveChoiceObservation(
        protagonist_name=protagonist_name,
        active_choice_evidence=active_evidence,
        cost_evidence=cost_evidence,
        passive_only=passive_only,
        passed=bool(active_evidence and not passive_only),
    )


def _concept_group_key(setting: dict[str, Any]) -> str:
    raw = str(
        setting.get("setting_name")
        or setting.get("setting_key")
        or setting.get("description")
        or ""
    ).strip()
    if not raw:
        return "unknown"
    return re.split(r"[：:（(——\-]", raw, maxsplit=1)[0].strip() or raw


def observe_concept_budget(
    content: str,
    new_settings: list[dict[str, Any]],
    *,
    max_new_core_concepts: int = 1,
) -> ConceptBudgetObservation:
    """Observe raw/core concept density for a chapter."""
    groups: dict[str, list[str]] = {}
    grounded_groups: set[str] = set()
    for setting in new_settings:
        group = _concept_group_key(setting)
        label = str(setting.get("setting_name") or setting.get("setting_key") or group)
        groups.setdefault(group, []).append(label)
        quote = str(setting.get("source_quote") or "").strip()
        name = str(setting.get("setting_name") or "").strip()
        if (quote and quote in content) or (name and name in content):
            grounded_groups.add(group)

    core_count = len(groups)
    grounded_count = len(grounded_groups)
    return ConceptBudgetObservation(
        max_new_core_concepts=max_new_core_concepts,
        raw_new_settings_count=len(new_settings),
        core_concept_count=core_count,
        grounded_new_concept_count=grounded_count,
        ungrounded_new_concept_count=max(core_count - grounded_count, 0),
        concept_groups=groups,
        passed=core_count <= max_new_core_concepts,
    )


async def audit_171w_text_guardrails(
    project_id: str,
    start: int,
    end: int,
    *,
    protagonist_name: str = "林渊",
) -> list[LiteraryGuardrailObservationRow]:
    """Audit 171w-c guardrail evidence from accepted text and DB facts."""
    async with get_db() as conn:
        conn.row_factory = lambda cursor, row: {  # type: ignore[assignment]  # aiosqlite row_factory stub mismatch
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cursor = await conn.execute(
            """SELECT h.chapter_number,
                      h.accepted_version_id,
                      v.content,
                      cb.supporting_character_goal,
                      cb.new_concept_budget
               FROM chapter_heads h
               LEFT JOIN chapter_versions v ON v.version_id = h.accepted_version_id
               LEFT JOIN creative_briefs cb ON cb.brief_id = v.creative_brief_id
               WHERE h.project_id = ?
                 AND h.chapter_number BETWEEN ? AND ?
               ORDER BY h.chapter_number""",
            (project_id, start, end),
        )
        chapter_rows = cast(
            dict[int, dict[str, Any]],
            {int(row["chapter_number"]): row for row in await cursor.fetchall()},
        )

        cursor = await conn.execute(
            """SELECT st.introduced_in_chapter AS chapter_number,
                      st.setting_key,
                      st.setting_name,
                      st.description,
                      ss.source_quote
               FROM setting_tracking st
               LEFT JOIN setting_snapshots ss
                 ON ss.project_id = st.project_id
                AND ss.setting_key = st.setting_key
               WHERE st.project_id = ?
                 AND st.introduced_in_chapter BETWEEN ? AND ?
               ORDER BY st.introduced_in_chapter, st.setting_key""",
            (project_id, start, end),
        )
        setting_rows = cast(list[dict[str, Any]], await cursor.fetchall())

    settings_by_chapter: dict[int, list[dict[str, Any]]] = {}
    seen_setting_keys: set[tuple[int, str]] = set()
    for row in setting_rows:
        key = (int(row["chapter_number"]), str(row["setting_key"]))
        if key in seen_setting_keys:
            continue
        seen_setting_keys.add(key)
        settings_by_chapter.setdefault(key[0], []).append(row)

    result: list[LiteraryGuardrailObservationRow] = []
    for chapter in range(start, end + 1):
        chapter_row: dict[str, Any] | None = chapter_rows.get(chapter)
        content = str(chapter_row["content"] or "") if chapter_row else ""
        supporting_goal = _loads_json(chapter_row["supporting_character_goal"], {}) if chapter_row else {}
        concept_budget = _loads_json(chapter_row["new_concept_budget"], {}) if chapter_row else {}
        max_new_core_concepts = int(concept_budget.get("max_new_core_concepts") or 1)
        result.append(
            LiteraryGuardrailObservationRow(
                chapter_number=chapter,
                accepted_version_id=chapter_row["accepted_version_id"] if chapter_row else None,
                supporting_goal=observe_supporting_character_goal(content, supporting_goal),
                active_choice=observe_active_choice(content, protagonist_name),
                concept_budget=observe_concept_budget(
                    content,
                    settings_by_chapter.get(chapter, []),
                    max_new_core_concepts=max_new_core_concepts,
                ),
            )
        )
    return result


def render_text_guardrail_observe_section(
    rows: list[LiteraryGuardrailObservationRow],
) -> str:
    """Render 171w-c observe checks as a compact markdown table."""
    lines = ["## 171w-c 正文护栏 observe", ""]
    if not rows:
        lines.append("（无 observe 数据）")
        return "\n".join(lines)

    supporting_failures = [
        row.chapter_number for row in rows if not row.supporting_goal.passed
    ]
    active_failures = [
        row.chapter_number for row in rows if not row.active_choice or not row.active_choice.passed
    ]
    concept_failures = [
        row.chapter_number for row in rows if not row.concept_budget.passed
    ]

    lines.append(
        f"- 配角目标通过：{len(rows) - len(supporting_failures)}/{len(rows)}；"
        f"主动选择通过：{len(rows) - len(active_failures)}/{len(rows)}；"
        f"概念预算通过：{len(rows) - len(concept_failures)}/{len(rows)}。"
    )
    lines.append("")
    lines.append("| 章 | 配角目标 | 主动选择 | raw/core 概念 |")
    lines.append("|----|----------|----------|---------------|")
    for row in rows:
        lines.append(
            f"| {row.chapter_number} | "
            f"{'OK' if row.supporting_goal.passed else 'MISSING'} | "
            f"{'OK' if row.active_choice and row.active_choice.passed else 'MISSING'} | "
            f"{row.concept_budget.raw_new_settings_count}/"
            f"{row.concept_budget.core_concept_count} |"
        )
    if supporting_failures:
        lines.append(f"- 配角目标缺口章：{supporting_failures}")
    if active_failures:
        lines.append(f"- 主动选择缺口章：{active_failures}")
    if concept_failures:
        lines.append(f"- 概念预算缺口章：{concept_failures}")
    return "\n".join(lines)


def check_supporting_character_goal_presence(
    content: str,
    brief: CreativeBrief | None,
    *,
    version_id: str = "",
) -> ReviewIssue | None:
    """Generate a patchable ReviewIssue if supporting character goal is missing.

    Returns None when:
    - No supporting_character_goal in the brief
    - The target character appears in the content
    - The character name is empty or only whitespace
    """
    if brief is None:
        return None
    goal = brief.supporting_character_goal
    if goal is None:
        return None
    target = (goal.character or "").strip()
    if not target:
        return None
    if target in content:
        return None
    evidence_quote = (
        f"目标配角「{target}」的目标：{goal.goal or '（未指定）'}；"
        f"与主角偏差：{goal.conflict_with_protagonist or '（未指定）'}。"
    )
    return ReviewIssue(
        issue_id=f"rule-guardrail-scg-{version_id}-{uuid.uuid4().hex[:6]}",
        category=ReviewCategory.CHARACTER_BEHAVIOR,
        severity="major",
        evidence_quote=evidence_quote,
        evidence_location="全章",
        issue_description=(
            f"配角目标护栏未命中——CreativeBrief 要求配角「{target}」出场"
            f"并以自己的目标改变局面，但正文中未出现该角色。"
        ),
        expected=(
            f"「{target}」应以姓名或稳定称谓出现在正文中，执行与主角目标"
            f"存在偏差的行动，造成信息延迟、路线变化、代价增加或误判。"
        ),
        actual=f"正文中未找到「{target}」。",
        suggested_fix=(
            f"在正文中插入「{target}」的出场与行动：该角色的目标与主角不同，"
            f"其行动应真实改变局面。不要只让该角色充当信息传递或情绪提醒。"
        ),
        fix_type="patch",
        confidence=1.0,
    )

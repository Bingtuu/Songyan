"""Input-side governance — settlement 后处理：超额 critical 降级与候选回升 (Task 149).

MVP：仅做可解释的计数阈值 + 证据匹配；不新增 LLM 调用、不新增 Agent、
不做显式 resolve/作废（Task 152）。状态更新集中在 service / repository。
"""

from __future__ import annotations

import aiosqlite
import structlog

from songyan.db.connection import get_db
from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.models.settlement import StateSettlement
from songyan.workflows._thread_economy import _settlement_resolved_text

logger = structlog.get_logger(__name__)


def _promotion_evidence_text(settlement: StateSettlement) -> str:
    """汇总本章 settlement 中可用于候选回升匹配的全部文本证据.

    与 ``_thread_economy._settlement_evidence_text`` 名义相近但**口径不同**：本函数
    额外纳入 ``source_quote``（回升匹配需要引文命中），故独立命名避免误用（#4）。
    """
    parts: list[str] = []
    for ns in settlement.new_settings:
        parts.append(ns.setting_name or "")
        parts.append(ns.description or "")
        parts.append(ns.source_quote or "")
    for cu in settlement.character_updates:
        parts.append(cu.new_value or "")
        parts.append(cu.source_quote or "")
    for fu in settlement.foreshadowing_updates:
        parts.append(fu.description or "")
    parts.extend(settlement.planted_hooks)
    parts.extend(settlement.resolved_hooks)
    parts.extend(settlement.open_threads)
    return "\n".join(p for p in parts if p)


def _candidate_terms(setting: dict[str, object]) -> set[str]:
    """提取候选设定可用于匹配的全部术语."""
    terms: set[str] = set()
    for field in ("setting_key", "setting_name", "description"):
        value = setting.get(field)
        if value:
            text = str(value).strip()
            if text:
                terms.add(text)
    return terms


def _exact_match(term: str, evidence_parts: list[str]) -> bool:
    """精确匹配：术语与证据某一段落（去空白后）完全一致."""
    normalized_term = term.strip().lower()
    if not normalized_term:
        return False
    return any(normalized_term == part.strip().lower() for part in evidence_parts if part.strip())


def _substring_match(term: str, evidence_text: str) -> bool:
    """子串匹配：术语在证据文本中出现过."""
    normalized_term = term.strip().lower()
    if not normalized_term:
        return False
    return normalized_term in evidence_text.lower()


# resolve 收束匹配的子串精度下限：短名词（如"灰塔"）频繁出现在无关章末钩子里，
# 仅凭裸子串命中就终态化会把主线 critical 过早误判 resolved（#2，参照 Task 144 加固）。
# 长度 < 该阈值的术语只允许精确整段命中，不允许裸子串命中。
_MIN_RESOLVE_SUBSTRING_LEN = 4


def _setting_matched_for_resolve(
    terms: set[str], evidence_parts: list[str], evidence_text: str
) -> bool:
    """判定某 critical 设定是否被收束证据可靠命中（收紧版，防过早 resolve）.

    - 任一术语与某段收束证据**精确整段相等** → 命中（强信号）。
    - 否则仅当术语长度 >= ``_MIN_RESOLVE_SUBSTRING_LEN`` 时才允许**子串**命中，
      避免 2-3 字短名词在无关钩子里被误命中而终态化。
    """
    for term in terms:
        if _exact_match(term, evidence_parts):
            return True
    for term in terms:
        if len(term.strip()) >= _MIN_RESOLVE_SUBSTRING_LEN and _substring_match(
            term, evidence_text
        ):
            return True
    return False


async def demote_overflow_new_settings(
    project_id: str,
    chapter_number: int,
    version_id: str,
    settlement: StateSettlement,
    setting_tracking_repo: SettingTrackingRepository | None = None,
    *,
    critical_cap: int = 3,
) -> list[str]:
    """After settlement, demote excess critical new_settings to 'candidate'.

    规则：
    - 仅处理本章新登记且 category='critical' 的 active 设定。
    - 保留前 critical_cap 条；超出的降级为 candidate。
    - 优先级：source_quote 非空者优先；同优先级下保持 settlement 原始顺序。

    Args:
        project_id: 项目 ID。
        chapter_number: 本章章节号。
        version_id: 关联 accepted 版本 ID（仅用于日志，降级不改变来源版本）。
        settlement: 本章结算结果。
        setting_tracking_repo: 可选注入的 repository。
        critical_cap: 单章 critical 新设定保留上限，默认 3。

    Returns:
        被降级的 setting_key 列表。
    """
    repo = setting_tracking_repo or SettingTrackingRepository()
    cap = max(0, critical_cap)

    # 本章 new_settings 总数都不超过 cap 时不可能超额，直接跳过全表操作（热路径，#perf）。
    if len(settlement.new_settings) <= cap:
        return []

    async with get_db() as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            """SELECT tracking_id, setting_key, category
               FROM setting_tracking
               WHERE project_id = ?
                 AND introduced_in_chapter = ?
                 AND status = 'active'""",
            (project_id, chapter_number),
        )
        rows = await cursor.fetchall()

    key_to_tracking: dict[str, dict[str, object]] = {
        str(row["setting_key"]): {
            "tracking_id": str(row["tracking_id"]),
            "category": str(row["category"]),
        }
        for row in rows
    }

    # 按 settlement.new_settings 顺序收集本章新增 critical，并标记证据完整度
    tiered: list[tuple[int, int, str, str]] = []  # (tier, index, setting_key, tracking_id)
    for idx, setting in enumerate(settlement.new_settings):
        key = setting.setting_key or setting.setting_name
        if not key or key not in key_to_tracking:
            continue
        tracking = key_to_tracking[key]
        if str(tracking["category"]) != "critical":
            continue
        has_evidence = bool(setting.source_quote and setting.source_quote.strip())
        tier = 0 if has_evidence else 1
        tiered.append((tier, idx, key, str(tracking["tracking_id"])))

    # 排序：tier 小优先，同 tier 按 settlement 原始顺序
    tiered.sort(key=lambda item: (item[0], item[1]))

    demoted_keys: list[str] = []
    for rank, (_, _, key, tracking_id) in enumerate(tiered):
        if rank < cap:
            continue
        await repo.update_status(tracking_id, "candidate")
        demoted_keys.append(key)

    if demoted_keys:
        logger.info(
            "input_side_governance.demoted_overflow_criticals",
            project_id=project_id,
            chapter_number=chapter_number,
            version_id=version_id,
            cap=cap,
            demoted_count=len(demoted_keys),
            demoted_keys=demoted_keys,
        )
    return demoted_keys


async def promote_candidate_settings_after_settlement(
    project_id: str,
    chapter_number: int,
    version_id: str,
    settlement: StateSettlement,
    setting_tracking_repo: SettingTrackingRepository | None = None,
) -> list[str]:
    """Promote candidate settings referenced in this chapter's evidence back to active.

    规则：
    - 只考虑**往期**遗留的候选（``introduced_in_chapter < chapter_number``）；本章刚被
      demote 的候选不参与回升，否则其证据必然命中本章 settlement、当章即把降级抵消（#1）。
    - 若 setting_key / setting_name / description 命中本章 settlement 证据文本，
      先尝试精确匹配，再尝试子串匹配。
    - 命中的候选回升为 active，并写回当前章/版本作为 source。

    Args:
        project_id: 项目 ID。
        chapter_number: 当前章节号。
        version_id: 当前 accepted 版本 ID。
        settlement: 本章结算结果（证据来源）。
        setting_tracking_repo: 可选注入的 repository。

    Returns:
        被回升的 setting_key 列表。
    """
    repo = setting_tracking_repo or SettingTrackingRepository()

    # 仅回升**往期**遗留的候选：本章刚被 demote 的候选（introduced_in_chapter==本章）
    # 其证据必然出现在本章 settlement 里，若参与回升会在同一章立即把降级抵消（#1 修复）。
    candidates = [
        s
        for s in await repo.list_by_project(project_id)
        if s.get("status", "active") == "candidate"
        and int(s.get("introduced_in_chapter") or 0) < chapter_number
    ]
    if not candidates:
        return []

    evidence_text = _promotion_evidence_text(settlement)
    evidence_parts = evidence_text.split("\n")

    promoted_keys: list[str] = []
    for candidate in candidates:
        terms = _candidate_terms(candidate)
        matched = False
        for term in terms:
            if _exact_match(term, evidence_parts):
                matched = True
                break
        if not matched:
            for term in terms:
                if _substring_match(term, evidence_text):
                    matched = True
                    break
        if not matched:
            continue

        tracking_id = str(candidate["tracking_id"])
        await repo.promote_to_active(tracking_id, chapter_number, version_id)
        promoted_keys.append(str(candidate["setting_key"]))

    if promoted_keys:
        logger.info(
            "input_side_governance.promoted_candidates",
            project_id=project_id,
            chapter_number=chapter_number,
            version_id=version_id,
            promoted_count=len(promoted_keys),
            promoted_keys=promoted_keys,
        )
    return promoted_keys


async def resolve_settings_after_settlement(
    project_id: str,
    chapter_number: int,
    version_id: str,
    settlement: StateSettlement,
    setting_tracking_repo: SettingTrackingRepository | None = None,
) -> list[str]:
    """Resolve critical settings that are addressed by this chapter's settlement evidence.

    收紧防过早 resolve（#2，参照 Task 144）：
    - 只考虑**往期**引入的 critical（``introduced_in_chapter < chapter_number``）；本章刚引入
      的 critical 不在同一章被收束（避免开局即终态化）。
    - 收束命中用 :func:`_setting_matched_for_resolve`：精确整段命中或长度达标的子串命中，
      短名词（<4 字）不允许裸子串命中，防止主线核心名词在无关钩子里被误判 resolved。

    Returns list of resolved setting_keys.
    """
    repo = setting_tracking_repo or SettingTrackingRepository()

    resolved_evidence_text = _settlement_resolved_text(settlement)
    # 无收束证据时直接返回，避免无谓的全表扫描（热路径每章都会走到，#perf）。
    if not resolved_evidence_text.strip():
        return []
    resolved_evidence_parts = resolved_evidence_text.split("\n")

    rows = [
        s
        for s in await repo.list_by_project(project_id)
        if s.get("status", "active") in ("active", "candidate")
        and s.get("category", "background") == "critical"
        and int(s.get("introduced_in_chapter") or 0) < chapter_number
    ]

    resolved_keys: list[str] = []
    for setting in rows:
        terms = _candidate_terms(setting)
        if not _setting_matched_for_resolve(
            terms, resolved_evidence_parts, resolved_evidence_text
        ):
            continue

        tracking_id = str(setting["tracking_id"])
        await repo.resolve_setting(tracking_id, chapter_number, version_id)
        resolved_keys.append(str(setting["setting_key"]))

    if resolved_keys:
        logger.info(
            "input_side_governance.resolved_settings",
            project_id=project_id,
            chapter_number=chapter_number,
            version_id=version_id,
            resolved_count=len(resolved_keys),
            resolved_keys=resolved_keys,
        )
    return resolved_keys


async def abandon_setting_explicitly(
    project_id: str,
    setting_key: str,
    chapter_number: int,
    reason: str,
    setting_tracking_repo: SettingTrackingRepository | None = None,
) -> None:
    """Abandon a critical setting by explicit external signal (outline/plan mark)."""
    repo = setting_tracking_repo or SettingTrackingRepository()

    row = next(
        (
            s
            for s in await repo.list_by_project(project_id)
            if s.get("setting_key") == setting_key
            and s.get("status", "active") in ("active", "candidate")
        ),
        None,
    )
    if row is None:
        raise ValueError(
            f"active/candidate setting not found: project={project_id}, key={setting_key}"
        )

    tracking_id = str(row["tracking_id"])
    await repo.abandon_setting(tracking_id, chapter_number, reason)
    logger.info(
        "input_side_governance.abandoned_setting_explicitly",
        project_id=project_id,
        chapter_number=chapter_number,
        setting_key=setting_key,
        reason=reason,
    )

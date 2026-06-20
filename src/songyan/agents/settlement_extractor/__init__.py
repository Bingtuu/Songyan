"""SettlementExtractor Agent — 章节 accept 后的结构化状态结算."""

from __future__ import annotations

import time
from typing import Any

import structlog

from songyan.db.context_repo import CharacterStateRepository
from songyan.db.settlement_repo import (
    ForeshadowingRepository,
    SettingSnapshotRepository,
)
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response
from songyan.models import (
    CharacterState,
    CharacterUpdate,
    ForeshadowingItem,
    ForeshadowingUpdate,
    GenreRules,
    NewSetting,
    NumericalUpdate,
    StateSettlement,
)
from songyan.utils.token_estimator import truncate_to_tokens

from ._apply import (
    _execute_with_db_retry as _execute_with_db_retry,
)
from ._apply import (
    _save_permanent_scenes as _save_permanent_scenes,
)
from ._apply import (
    apply_settlement as apply_settlement,
)
from ._quote_filter import filter_settlement_source_quotes
from ._setting_quality import _normalize_setting_key
from ._validate import _validate_settlement

logger = structlog.get_logger(__name__)

MAX_CONTENT_TOKENS = 6000
MAX_PROMPT_CHARACTER_STATES = 40
MAX_PROMPT_SETTINGS = 40
MAX_PROMPT_FORESHADOWINGS = 30
FORESHADOWING_DUE_WINDOW = 5


def _load_prompt_template() -> str:
    """加载 SettlementExtractor Prompt 模板 — 已迁移到工艺卡系统."""
    from songyan.prompts import get_prompt_loader
    return get_prompt_loader().load_card("settlement_extractor").system_prompt


async def _load_current_character_states(
    char_state_repo: CharacterStateRepository,
    project_id: str,
) -> list[CharacterState]:
    """加载项目下每个角色的最新状态."""
    return await char_state_repo.list_latest_by_project(project_id)


async def _load_current_settings(
    setting_repo: SettingSnapshotRepository,
    project_id: str,
) -> list[NewSetting]:
    """加载项目下已揭示的设定."""
    return await setting_repo.list_by_project(project_id)


async def _load_current_foreshadowings(
    foreshadowing_repo: ForeshadowingRepository,
    project_id: str,
) -> list[ForeshadowingItem]:
    """加载项目下活跃的伏笔."""
    return await foreshadowing_repo.list_active(project_id)


def _render_character_states(states: list[CharacterState]) -> str:
    """渲染角色状态列表."""
    if not states:
        return "（无角色状态记录）"
    lines: list[str] = []
    for s in states:
        lines.append(f"- {s.character_id} | {s.field}: {s.value}")
    return "\n".join(lines)


def _render_settings(settings: list[NewSetting]) -> str:
    """渲染设定列表."""
    if not settings:
        return "（无已揭示设定）"
    lines: list[str] = []
    for s in settings:
        lines.append(f"- {s.setting_name} ({s.setting_key}): {s.description}")
    return "\n".join(lines)


def _render_foreshadowings(items: list[ForeshadowingItem]) -> str:
    """渲染伏笔列表."""
    if not items:
        return "（无活跃伏笔）"
    lines: list[str] = []
    for item in items:
        if item.expected_resolve_chapter:
            status = f"[预计第{item.expected_resolve_chapter}章回收]"
        else:
            status = ""
        lines.append(
            f"- {item.foreshadowing_id}: {item.description} {status}"
        )
    return "\n".join(lines)


def _render_genre_rules(genre_rules: GenreRules | None) -> str:
    """渲染题材规则."""
    if genre_rules is None:
        return "（无特殊题材规则）"
    lines: list[str] = []
    if genre_rules.pacing_rule:
        lines.append(f"- 节奏规则：{genre_rules.pacing_rule}")
    if genre_rules.writer_rules:
        lines.append(f"- 写作规则：{', '.join(genre_rules.writer_rules)}")
    if genre_rules.fatigue_words:
        lines.append(f"- 疲劳词：{', '.join(genre_rules.fatigue_words)}")
    return "\n".join(lines) if lines else "（无特殊题材规则）"



def _matches_content(content_lower: str, *values: object) -> bool:
    """判断字段值是否在正文中出现，用于 prompt-only 事实源过滤."""
    for value in values:
        if value is None:
            continue
        text = str(value).strip().lower()
        if text and text in content_lower:
            return True
    return False


def _select_prompt_character_states(
    content: str,
    states: list[CharacterState],
    limit: int = MAX_PROMPT_CHARACTER_STATES,
) -> list[CharacterState]:
    """选择进入 Settlement prompt 的角色状态，验证仍使用全量 states."""
    if len(states) <= limit:
        return states
    content_lower = content.lower()
    matched = [
        state
        for state in states
        if _matches_content(
            content_lower,
            state.character_id,
            state.field,
            state.value,
            state.source_version_id,
        )
    ]
    selected: list[CharacterState] = []
    seen: set[tuple[str, str]] = set()
    for state in [*matched, *states]:
        key = (state.character_id, state.field)
        if key in seen:
            continue
        seen.add(key)
        selected.append(state)
        if len(selected) >= limit:
            break
    return selected


def _select_prompt_settings(
    content: str,
    settings: list[NewSetting],
    limit: int = MAX_PROMPT_SETTINGS,
) -> list[NewSetting]:
    """选择进入 Settlement prompt 的设定，验证仍使用全量 settings."""
    if len(settings) <= limit:
        return settings
    content_lower = content.lower()
    matched = [
        setting
        for setting in settings
        if _matches_content(
            content_lower,
            setting.setting_name,
            setting.setting_key,
            setting.description,
            setting.source_quote,
        )
    ]
    recent = sorted(settings, key=lambda item: item.chapter_number, reverse=True)
    selected: list[NewSetting] = []
    seen: set[str] = set()
    for setting in [*matched, *recent]:
        key = setting.setting_key or setting.setting_name
        if key in seen:
            continue
        seen.add(key)
        selected.append(setting)
        if len(selected) >= limit:
            break
    return selected


def _foreshadowing_priority(
    item: ForeshadowingItem,
    content_lower: str,
    chapter_number: int,
) -> tuple[int, int, int]:
    content_hit = _matches_content(
        content_lower,
        item.foreshadowing_id,
        item.description,
    )
    due = item.expected_resolve_chapter
    due_soon = due is not None and due <= chapter_number + FORESHADOWING_DUE_WINDOW
    due_distance = abs((due or chapter_number) - chapter_number)
    priority = 0 if content_hit or due_soon or item.status == "due" else 1
    return (priority, due_distance, -item.planted_in_chapter)


def _select_prompt_foreshadowings(
    content: str,
    foreshadowings: list[ForeshadowingItem],
    chapter_number: int,
    limit: int = MAX_PROMPT_FORESHADOWINGS,
) -> list[ForeshadowingItem]:
    """选择进入 Settlement prompt 的伏笔，优先 due/正文命中/近期."""
    if len(foreshadowings) <= limit:
        return foreshadowings
    content_lower = content.lower()
    ranked = sorted(
        foreshadowings,
        key=lambda item: _foreshadowing_priority(item, content_lower, chapter_number),
    )
    return ranked[:limit]


def _select_prompt_facts(
    content: str,
    chapter_number: int,
    states: list[CharacterState],
    settings: list[NewSetting],
    foreshadowings: list[ForeshadowingItem],
) -> tuple[list[CharacterState], list[NewSetting], list[ForeshadowingItem]]:
    """限制 Settlement prompt 事实源规模，不影响后续代码验证."""
    return (
        _select_prompt_character_states(content, states),
        _select_prompt_settings(content, settings),
        _select_prompt_foreshadowings(content, foreshadowings, chapter_number),
    )

def _render_prompt(
    content: str,
    version_id: str,
    current_states: list[CharacterState],
    current_settings: list[NewSetting],
    current_foreshadowings: list[ForeshadowingItem],
    genre_rules: GenreRules | None,
) -> str:
    """渲染 SettlementExtractor Prompt."""
    from songyan.prompts import get_prompt_loader

    loader = get_prompt_loader()
    card = loader.load_card("settlement_extractor")

    content = truncate_to_tokens(content, MAX_CONTENT_TOKENS)

    rendered = loader.render_card(card, {
        "content": content,
        "version_id": version_id,
        "current_character_states": _render_character_states(current_states),
        "current_settings": _render_settings(current_settings),
        "current_foreshadowings": _render_foreshadowings(current_foreshadowings),
        "genre_rules": _render_genre_rules(genre_rules),
    })
    return rendered.full_prompt


# Task 094: Character ID 标准化映射
# 长期方案应在 characters 表中增加 aliases 字段
_CHARACTER_ID_ALIASES: dict[str, str] = {}


def register_character_aliases(aliases: dict[str, str]) -> None:
    """注册角色 ID 别名映射（应在项目初始化时调用）."""
    _CHARACTER_ID_ALIASES.update(aliases)


def _normalize_character_id(raw_id: str) -> str:
    """将别名映射为标准 ID."""
    return _CHARACTER_ID_ALIASES.get(raw_id, raw_id)


def _build_character_update(data: dict[str, Any]) -> CharacterUpdate | None:
    """从字典构建 CharacterUpdate."""
    if not isinstance(data, dict):
        return None
    character_id = _normalize_character_id(data.get("character_id", ""))
    field = data.get("field", "")
    if not character_id or not field:
        return None
    return CharacterUpdate(
        character_id=character_id,
        field=field,
        old_value=str(data.get("old_value", "")),
        new_value=str(data.get("new_value", "")),
        source_quote=data.get("source_quote", ""),
    )


def _build_new_setting(data: dict[str, Any]) -> NewSetting | None:
    """从字典构建 NewSetting."""
    if not isinstance(data, dict):
        return None
    setting_name = data.get("setting_name", "")
    if not setting_name:
        return None
    return NewSetting(
        setting_name=setting_name,
        description=data.get("description", ""),
        source_quote=data.get("source_quote", ""),
        setting_key=data.get("setting_key", ""),
    )


def _build_foreshadowing_update(data: dict[str, Any]) -> ForeshadowingUpdate | None:
    """从字典构建 ForeshadowingUpdate."""
    if not isinstance(data, dict):
        return None
    operation = data.get("operation", "")
    if operation not in ("plant", "resolve", "update_status"):
        return None
    return ForeshadowingUpdate(
        foreshadowing_id=data.get("foreshadowing_id"),
        operation=operation,  # type: ignore[arg-type]
        description=data.get("description", ""),
        expected_resolve_chapter=data.get("expected_resolve_chapter"),
        source_version_id=data.get("source_version_id", ""),
    )


def _build_increment(data: dict[str, Any]) -> Any:
    """从字典构建 Increment."""
    if not isinstance(data, dict):
        return None
    from songyan.models import Increment

    return Increment(
        amount=float(data.get("amount", 0.0)),
        source=data.get("source", ""),
        source_quote=data.get("source_quote", ""),
    )


def _build_decrement(data: dict[str, Any]) -> Any:
    """从字典构建 Decrement."""
    if not isinstance(data, dict):
        return None
    from songyan.models import Decrement

    return Decrement(
        amount=float(data.get("amount", 0.0)),
        usage=data.get("usage", ""),
        source_quote=data.get("source_quote", ""),
    )


def _build_numerical_update(data: dict[str, Any]) -> NumericalUpdate | None:
    """从字典构建 NumericalUpdate."""
    if not isinstance(data, dict):
        return None
    character_id = data.get("character_id", "")
    attribute_name = data.get("attribute_name", "")
    if not character_id or not attribute_name:
        return None
    increments = [
        _build_increment(item)
        for item in data.get("increments", [])
        if isinstance(item, dict)
    ]
    decrements = [
        _build_decrement(item)
        for item in data.get("decrements", [])
        if isinstance(item, dict)
    ]
    return NumericalUpdate(
        character_id=character_id,
        attribute_name=attribute_name,
        opening_value=float(data.get("opening_value", 0.0)),
        increments=increments,
        decrements=decrements,
        closing_value=float(data.get("closing_value", 0.0)),
    )


def _normalize_hooks(hooks: list[Any]) -> list[str]:
    """兼容 LLM 返回字符串或 dict 的 hook 格式."""
    result: list[str] = []
    for h in hooks:
        if isinstance(h, str):
            result.append(h)
        elif isinstance(h, dict):
            for key in ("description", "text", "hook_text", "content", "hook_type"):
                if key in h and isinstance(h[key], str):
                    result.append(h[key])
                    break
            else:
                result.append(str(h))
        else:
            result.append(str(h))
    return result


def _build_state_settlement(data: dict[str, Any]) -> StateSettlement:
    """从解析后的字典构建 StateSettlement."""
    character_updates = [
        u for u in (_build_character_update(item) for item in data.get("character_updates", []))
        if u is not None
    ]
    new_settings = [
        s for s in (_build_new_setting(item) for item in data.get("new_settings", []))
        if s is not None
    ]
    foreshadowing_updates = [
        f for f in (
            _build_foreshadowing_update(item)
            for item in data.get("foreshadowing_updates", [])
        )
        if f is not None
    ]
    numerical_updates = [
        n for n in (_build_numerical_update(item) for item in data.get("numerical_updates", []))
        if n is not None
    ]
    return StateSettlement(
        character_updates=character_updates,
        new_settings=new_settings,
        foreshadowing_updates=foreshadowing_updates,
        numerical_updates=numerical_updates,
        planted_hooks=_normalize_hooks(data.get("planted_hooks", [])),
        resolved_hooks=_normalize_hooks(data.get("resolved_hooks", [])),
    )


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------
async def extract_settlement(
    content: str,
    project_id: str,
    chapter_number: int,
    version_id: str,
    genre_rules: GenreRules | None = None,
    temperature: float = 0.3,
) -> StateSettlement:
    """执行状态结算 — LLM 提取 + 代码验证.

    Args:
        content: accepted 章节正文
        project_id: 项目 ID
        chapter_number: 章节号
        version_id: accepted 版本 ID（写入 source_version_id）
        genre_rules: 题材规则（可选）
        temperature: LLM 温度（默认 0.3，精确提取）

    Returns:
        StateSettlement（含 validation_status 和 validation_errors）
    """
    start_time = time.perf_counter()

    # 1. 加载当前状态
    char_state_repo = CharacterStateRepository()
    setting_repo = SettingSnapshotRepository()
    foreshadowing_repo = ForeshadowingRepository()

    current_states = await _load_current_character_states(char_state_repo, project_id)
    current_settings = await _load_current_settings(setting_repo, project_id)
    current_foreshadowings = await _load_current_foreshadowings(foreshadowing_repo, project_id)

    logger.info(
        "settlement.context_loaded",
        project_id=project_id,
        states_count=len(current_states),
        settings_count=len(current_settings),
        foreshadowings_count=len(current_foreshadowings),
    )

    prompt_states, prompt_settings, prompt_foreshadowings = _select_prompt_facts(
        content,
        chapter_number,
        current_states,
        current_settings,
        current_foreshadowings,
    )
    logger.info(
        "settlement.prompt_facts_selected",
        states_count=len(prompt_states),
        settings_count=len(prompt_settings),
        foreshadowings_count=len(prompt_foreshadowings),
    )

    # 2. 渲染 Prompt
    prompt = _render_prompt(
        content, version_id, prompt_states, prompt_settings,
        prompt_foreshadowings, genre_rules,
    )
    # 3. 调用 LLM
    llm_response = await call_llm(prompt, temperature=temperature)
    data = parse_llm_response(llm_response)

    # 4. 构建 StateSettlement
    settlement = _build_state_settlement(data)

    # Task 112: setting_key 必须在 validation 前规范化。
    # apply_settlement 仍保留幂等规范化作为写库前防线。
    normalized_settings: list[NewSetting] = []
    for setting in settlement.new_settings:
        normalized_key = _normalize_setting_key(
            setting.setting_key, setting.setting_name
        )
        if normalized_key is None:
            logger.warning(
                "settlement.setting_key_discarded_before_validation",
                setting_name=setting.setting_name,
                original_key=setting.setting_key,
                project_id=project_id,
                chapter_number=chapter_number,
            )
            continue
        setting.setting_key = normalized_key
        normalized_settings.append(setting)
    settlement.new_settings = normalized_settings

    # 4.3. Task 094: 代码层去重 — 跳过已存在的 setting_key
    existing_keys = {s.setting_key for s in current_settings if s.setting_key}
    duplicates = [s for s in settlement.new_settings if s.setting_key in existing_keys]
    if duplicates:
        settlement.new_settings = [
            s for s in settlement.new_settings if s.setting_key not in existing_keys
        ]
        logger.info(
            "settlement.duplicates_skipped",
            count=len(duplicates),
            keys=[s.setting_key for s in duplicates],
            project_id=project_id,
            chapter_number=chapter_number,
        )

    # 4.5. source_quote 去噪（072）
    # Task 114a: filter_settlement_source_quotes 现为 async，需 await
    filtered = await filter_settlement_source_quotes(settlement, content)
    if filtered > 0:
        logger.info(
            "settlement.source_quotes_filtered",
            filtered_count=filtered,
            project_id=project_id,
            chapter_number=chapter_number,
        )

    # 5. 代码验证
    errors = await _validate_settlement(
        settlement, content, current_states, current_settings,
        chapter_number=chapter_number,
        project_id=project_id,
    )

    if errors:
        settlement.validation_status = "needs_human_review"
        settlement.validation_errors = errors
        logger.warning(
            "settlement.validation_failed",
            error_count=len(errors),
            errors=errors,
        )
    else:
        settlement.validation_status = "valid"
        logger.info("settlement.validation_passed")

    # 6. Phase 4: 计算影响力评分与开放线索
    settlement.impact_score = _calculate_impact_score(settlement)
    settlement.open_threads = _extract_open_threads(settlement, chapter_number)

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "settlement.done",
        character_updates=len(settlement.character_updates),
        new_settings=len(settlement.new_settings),
        foreshadowing_updates=len(settlement.foreshadowing_updates),
        numerical_updates=len(settlement.numerical_updates),
        validation_status=settlement.validation_status,
        impact_score=settlement.impact_score,
        open_threads=len(settlement.open_threads),
        duration_ms=duration_ms,
    )
    return settlement


# ---------------------------------------------------------------------------
# Phase 4: Impact Score & Open Threads
# ---------------------------------------------------------------------------

_UPHEAVAL_KEYWORDS = ["颠覆", "改变", "真相", "revelation", "世界观", "秘密"]
_DEATH_INJURY_KEYWORDS = ["死亡", "重伤", "残废", "濒死", "牺牲", "陨落"]
_MYSTERY_KEYWORDS = ["秘密", "未知", "谜团", "真相", "尚未", "隐藏", "幕后"]


def _calculate_impact_score(settlement: StateSettlement) -> float:
    """基于 settlement 内容计算本章影响力评分 (0.0~1.0)."""
    score = 0.0
    # 世界观颠覆
    for s in settlement.new_settings:
        if any(kw in s.description for kw in _UPHEAVAL_KEYWORDS):
            score += 0.5
    # 角色死亡/重伤
    for cu in settlement.character_updates:
        if any(kw in cu.new_value for kw in _DEATH_INJURY_KEYWORDS):
            score += 0.4
    # 新设定首次出现（每个 +0.05，上限 0.15）
    score += min(len(settlement.new_settings) * 0.05, 0.15)
    # 伏笔埋设（每个 +0.03，上限 0.09）
    planted = [fs for fs in settlement.foreshadowing_updates if fs.operation == "plant"]
    score += min(len(planted) * 0.03, 0.09)
    return min(score, 1.0)


def _extract_open_threads(settlement: StateSettlement, chapter_number: int) -> list[str]:
    """从 settlement 中提取未完结线索描述."""
    threads: list[str] = []
    for fu in settlement.foreshadowing_updates:
        if fu.operation == "plant":
            threads.append(f"伏笔：{fu.description}")
    for ns in settlement.new_settings:
        if any(kw in ns.description for kw in _MYSTERY_KEYWORDS):
            threads.append(f"设定：{ns.setting_name} — {ns.description}")
    for cu in settlement.character_updates:
        if cu.field.lower() in ("goal", "目标", "任务", "使命"):
            threads.append(f"角色目标：{cu.character_id} 的 {cu.new_value}")
    return threads

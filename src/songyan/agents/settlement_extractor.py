"""SettlementExtractor Agent — 章节 accept 后的结构化状态结算."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from songyan.db.context_repo import CharacterStateRepository
from songyan.db.repository import CharacterRepository
from songyan.db.settlement_repo import (
    ForeshadowingRepository,
    NumericalLedgerRepository,
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

logger = structlog.get_logger(__name__)

MAX_CONTENT_LENGTH = 8000


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

    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH] + "\n...（正文已截断）"

    rendered = loader.render_card(card, {
        "content": content,
        "version_id": version_id,
        "current_character_states": _render_character_states(current_states),
        "current_settings": _render_settings(current_settings),
        "current_foreshadowings": _render_foreshadowings(current_foreshadowings),
        "genre_rules": _render_genre_rules(genre_rules),
    })
    return rendered.full_prompt


def _build_character_update(data: dict[str, Any]) -> CharacterUpdate | None:
    """从字典构建 CharacterUpdate."""
    character_id = data.get("character_id", "")
    field = data.get("field", "")
    if not character_id or not field:
        return None
    return CharacterUpdate(
        character_id=character_id,
        field=field,
        old_value=data.get("old_value", ""),
        new_value=data.get("new_value", ""),
        source_quote=data.get("source_quote", ""),
    )


def _build_new_setting(data: dict[str, Any]) -> NewSetting | None:
    """从字典构建 NewSetting."""
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
    from songyan.models import Increment

    return Increment(
        amount=float(data.get("amount", 0.0)),
        source=data.get("source", ""),
        source_quote=data.get("source_quote", ""),
    )


def _build_decrement(data: dict[str, Any]) -> Any:
    """从字典构建 Decrement."""
    from songyan.models import Decrement

    return Decrement(
        amount=float(data.get("amount", 0.0)),
        usage=data.get("usage", ""),
        source_quote=data.get("source_quote", ""),
    )


def _build_numerical_update(data: dict[str, Any]) -> NumericalUpdate | None:
    """从字典构建 NumericalUpdate."""
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
        planted_hooks=data.get("planted_hooks", []),
        resolved_hooks=data.get("resolved_hooks", []),
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
async def _validate_settlement(
    settlement: StateSettlement,
    content: str,
    current_states: list[CharacterState],
    current_settings: list[NewSetting],
) -> list[str]:
    """验证结算结果，返回错误列表."""
    errors: list[str] = []

    # 1. 验证 character_update.old_value
    state_map: dict[tuple[str, str], str] = {
        (s.character_id, s.field): s.value for s in current_states
    }
    for update in settlement.character_updates:
        key = (update.character_id, update.field)
        if key in state_map and state_map[key] != update.old_value:
            errors.append(
                f"角色 {update.character_id} 的 {update.field} "
                f"当前值为 '{state_map[key]}'，"
                f"但结算声称 old_value='{update.old_value}'"
            )

    # 2. 验证 source_quote 在正文中存在
    for update in settlement.character_updates:
        if update.source_quote and update.source_quote not in content:
            errors.append(
                f"角色 {update.character_id} 的 source_quote "
                f"未在正文中找到: '{update.source_quote[:50]}...'"
            )
    for setting in settlement.new_settings:
        if setting.source_quote and setting.source_quote not in content:
            errors.append(
                f"设定 '{setting.setting_name}' 的 source_quote "
                f"未在正文中找到: '{setting.source_quote[:50]}...'"
            )

    # 3. 验证 setting_key 唯一
    existing_keys = {s.setting_key for s in current_settings if s.setting_key}
    for setting in settlement.new_settings:
        if setting.setting_key and setting.setting_key in existing_keys:
            errors.append(
                f"设定 key '{setting.setting_key}' 已存在，"
                f"不能重复登记"
            )

    # 4. 验证 numerical_update.closing_value 公式
    for num in settlement.numerical_updates:
        expected = (
            num.opening_value
            + sum(i.amount for i in num.increments)
            - sum(d.amount for d in num.decrements)
        )
        if abs(num.closing_value - expected) > 0.001:
            errors.append(
                f"角色 {num.character_id} 的 {num.attribute_name} "
                f"closing_value ({num.closing_value}) 不等于 "
                f"公式值 ({expected:.3f})"
            )

    # 5. 验证 foreshadowing_update.source_version_id
    for fs in settlement.foreshadowing_updates:
        if not fs.source_version_id:
            errors.append(
                f"伏笔 '{fs.description[:30]}...' 的 source_version_id 为空"
            )

    return errors


# ---------------------------------------------------------------------------
# Apply Settlement
# ---------------------------------------------------------------------------
async def apply_settlement(
    settlement: StateSettlement,
    project_id: str,
    chapter_number: int,
    version_id: str,
    char_repo: CharacterRepository | None = None,
    setting_repo: SettingSnapshotRepository | None = None,
    foreshadowing_repo: ForeshadowingRepository | None = None,
    numerical_repo: NumericalLedgerRepository | None = None,
) -> None:
    """将验证通过的结算结果应用到数据库 — INSERT 新快照，不 UPDATE 旧记录.

    Args:
        settlement: 验证通过的 StateSettlement
        project_id: 项目 ID
        chapter_number: 章节号
        version_id: 关联版本 ID
    """
    if char_repo is None:
        char_repo = CharacterRepository()
    if setting_repo is None:
        setting_repo = SettingSnapshotRepository()
    if foreshadowing_repo is None:
        foreshadowing_repo = ForeshadowingRepository()
    if numerical_repo is None:
        numerical_repo = NumericalLedgerRepository()

    # 1. 角色状态变更 — INSERT 新快照
    for update in settlement.character_updates:
        state = CharacterState(
            character_id=update.character_id,
            field=update.field,
            value=update.new_value,
            source_version_id=version_id,
        )
        await char_repo.add_state_snapshot(state)
        logger.info(
            "settlement.character_state_inserted",
            character_id=update.character_id,
            field=update.field,
            value=update.new_value,
        )

    # 2. 新设定登记 — INSERT
    for setting in settlement.new_settings:
        setting_id = f"set-{project_id}-{uuid.uuid4().hex[:8]}"
        await setting_repo.create(setting, project_id, setting_id)
        logger.info(
            "settlement.setting_inserted",
            setting_id=setting_id,
            setting_name=setting.setting_name,
        )

    # 3. 伏笔操作 — plant 时 INSERT，resolve 时 UPDATE
    for fs in settlement.foreshadowing_updates:
        if fs.operation == "plant":
            fs_id = fs.foreshadowing_id or f"fs-{project_id}-{uuid.uuid4().hex[:8]}"
            item = ForeshadowingItem(
                foreshadowing_id=fs_id,
                description=fs.description,
                planted_in_chapter=chapter_number,
                expected_resolve_chapter=fs.expected_resolve_chapter,
                status="planted",
            )
            await foreshadowing_repo.create(item, project_id, version_id)
            logger.info("settlement.foreshadowing_planted", foreshadowing_id=fs_id)
        elif fs.operation == "resolve" and fs.foreshadowing_id:
            await foreshadowing_repo.update_status(fs.foreshadowing_id, "resolved")
            logger.info("settlement.foreshadowing_resolved", foreshadowing_id=fs.foreshadowing_id)

    # 4. 数值变更 — INSERT
    for num in settlement.numerical_updates:
        ledger_id = f"num-{project_id}-{chapter_number}-{uuid.uuid4().hex[:8]}"
        await numerical_repo.create(num, project_id, chapter_number, ledger_id)
        logger.info(
            "settlement.numerical_inserted",
            ledger_id=ledger_id,
            character_id=num.character_id,
            attribute=num.attribute_name,
        )

    logger.info("settlement.applied", project_id=project_id, chapter_number=chapter_number)


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

    # 2. 渲染 Prompt
    prompt = _render_prompt(
        content, version_id, current_states, current_settings,
        current_foreshadowings, genre_rules,
    )

    # 3. 调用 LLM
    llm_response = await call_llm(prompt, temperature=temperature)
    data = parse_llm_response(llm_response)

    # 4. 构建 StateSettlement
    settlement = _build_state_settlement(data)

    # 5. 代码验证
    errors = await _validate_settlement(
        settlement, content, current_states, current_settings,
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

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "settlement.done",
        character_updates=len(settlement.character_updates),
        new_settings=len(settlement.new_settings),
        foreshadowing_updates=len(settlement.foreshadowing_updates),
        numerical_updates=len(settlement.numerical_updates),
        validation_status=settlement.validation_status,
        duration_ms=duration_ms,
    )
    return settlement

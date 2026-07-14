"""从 ProjectTemplate 初始化数据库项目."""

from __future__ import annotations

import uuid

import structlog

from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import (
    CharacterRepository,
    ProjectRepository,
)
from songyan.db.settlement_repo import (
    NumericalLedgerRepository,
    SettingSnapshotRepository,
)
from songyan.models import (
    ArcPlan,
    Character,
    NewSetting,
    NumericalUpdate,
    PlotThread,
    ProjectSetting,
)
from songyan.models.character import DialogueStyleCard
from songyan.models.project_template import ProjectTemplate
from songyan.workflows._helpers import ensure_protagonist_character, new_id

logger = structlog.get_logger(__name__)


class ProjectInitializer:
    """从模板创建完整项目."""

    @staticmethod
    async def from_template(template: ProjectTemplate) -> tuple[str, ProjectSetting]:
        """从模板创建完整项目，返回 (project_id, project_setting)."""
        await init_schema()

        project_id = uuid.uuid4().hex
        await ProjectRepository().create(template.project_setting, project_id)
        logger.info(
            "project_initialized_from_template",
            project_id=project_id,
            template_id=template.id,
        )

        # 创建 protagonist Character（与 CLI 行为一致）
        await ensure_protagonist_character(project_id, template.project_setting)

        # 写入 seed 角色
        await _import_seed_characters(template, project_id)

        # 写入 seed 设定
        await _import_seed_settings(template, project_id)

        # 写入数值体系初始 ledger
        await _import_seed_numerical_system(template, project_id)

        # 导入大纲
        if template.has_outline:
            outline_tuple = template.outline_tuple
            assert outline_tuple is not None
            outline, arcs, threads = outline_tuple
            # outline 是 dummy project_id 加载的，需要替换为真实 project_id
            outline.project_id = project_id
            # 线索 ID 在全局唯一，多项目共库时会冲突；按项目作用域前缀化
            threads, arcs = _prefix_thread_ids(project_id, threads, arcs)
            for arc in arcs:
                arc.project_id = project_id
                if arc.arc_id.startswith("dummy-"):
                    arc.arc_id = arc.arc_id.replace("dummy", project_id, 1)
            await NarrativeRepository().import_outline(project_id, outline, arcs, threads)

        return project_id, template.project_setting


async def _import_seed_characters(template: ProjectTemplate, project_id: str) -> None:
    char_repo = CharacterRepository()
    existing_names = {c.name for c in await char_repo.list_by_project(project_id)}
    for seed_char in template.seed.characters:
        if seed_char.name in existing_names:
            continue
        char_id = new_id("char")
        char = Character(
            character_id=char_id,
            project_id=project_id,
            name=seed_char.name,
            role_type=seed_char.role,
            background=seed_char.description,
            personality_traits=[],
            goals=[],
            relationships={},
            dialogue_style_card=DialogueStyleCard(
                character_id=char_id,
                project_id=project_id,
                sentence_length_preference="mixed",
                common_openers=[],
                common_closers=[],
            ),
        )
        await char_repo.create(char)


async def _import_seed_settings(template: ProjectTemplate, project_id: str) -> None:
    setting_repo = SettingSnapshotRepository()
    keys: set[str] = set()
    for seed_setting in template.seed.initial_settings:
        if seed_setting.setting_key in keys:
            logger.warning(
                "duplicate_seed_setting_key",
                project_id=project_id,
                key=seed_setting.setting_key,
            )
            continue
        keys.add(seed_setting.setting_key)
        setting = NewSetting(
            setting_name=seed_setting.setting_name,
            description=seed_setting.description,
            source_quote=seed_setting.source_quote,
            setting_key=seed_setting.setting_key,
        )
        setting_id = new_id("set")
        await setting_repo.create(setting, project_id, setting_id)


async def _import_seed_numerical_system(
    template: ProjectTemplate, project_id: str
) -> None:
    if template.seed.numerical_system is None:
        return
    char_repo = CharacterRepository()
    characters = await char_repo.list_by_project(project_id)
    name_to_char = {c.name: c for c in characters}
    numerical_repo = NumericalLedgerRepository()

    for seed_char in template.seed.characters:
        char = name_to_char.get(seed_char.name)
        if char is None:
            continue
        for field, value in (seed_char.initial_state or {}).items():
            try:
                opening = float(value)
            except (ValueError, TypeError):
                continue
            update = NumericalUpdate(
                character_id=char.character_id,
                attribute_name=field,
                opening_value=opening,
                closing_value=opening,
            )
            ledger_id = new_id("num")
            await numerical_repo.create(update, project_id, 0, ledger_id)


def _prefix_thread_ids(
    project_id: str,
    threads: list[PlotThread],
    arcs: list[ArcPlan],
) -> tuple[list[PlotThread], list[ArcPlan]]:
    """把线索 ID 加上项目前缀，避免同一数据库中多项目冲突.

    同时更新 arc_plans 中对线索的引用。返回深拷贝后的新对象，不污染模板实例。
    """
    mapping: dict[str, str] = {}
    new_threads: list[PlotThread] = []
    for thread in threads:
        new_id_val = f"{project_id}-{thread.thread_id}"
        mapping[thread.thread_id] = new_id_val
        new_threads.append(
            thread.model_copy(
                update={"project_id": project_id, "thread_id": new_id_val}, deep=True
            )
        )

    new_arcs: list[ArcPlan] = []
    for arc in arcs:
        new_open = [mapping.get(tid, tid) for tid in arc.threads_to_open]
        new_resolve = [mapping.get(tid, tid) for tid in arc.threads_to_resolve]
        new_arcs.append(
            arc.model_copy(
                update={
                    "project_id": project_id,
                    "threads_to_open": new_open,
                    "threads_to_resolve": new_resolve,
                },
                deep=True,
            )
        )

    return new_threads, new_arcs

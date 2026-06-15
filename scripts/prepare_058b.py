"""Task 058b 运行前准备 — 导入 scifi seed 项目 + Ch1 到主数据库."""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.runner import import_seed_project, import_seed_chapter
from evals.models import SeedProjectConfig
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.repository import CharacterRepository
from songyan.models import CharacterState

SEED_CONFIG = "evals/seeds/scifi_new_weird.json"
SEED_CHAPTER = "evals/seeds/chapters/scifi_new_weird_ch1.md"


async def _import_seed_character_states(project_id: str, source_version_id: str) -> None:
    """写入角色初始状态快照."""
    config = SeedProjectConfig.model_validate_json(
        Path(SEED_CONFIG).read_text(encoding="utf-8")
    )
    char_repo = CharacterRepository()
    characters = await char_repo.list_by_project(project_id)

    for char in characters:
        seed_char = next((sc for sc in config.characters if sc.name == char.name), None)
        if seed_char is None:
            continue
        for field, value in (seed_char.initial_state or {}).items():
            state = CharacterState(
                character_id=char.character_id,
                field=field,
                value=str(value),
                source_version_id=source_version_id,
            )
            await char_repo.add_state_snapshot(state)

    print(f"   角色初始状态已导入: {len(characters)} 个角色")


async def main() -> str:
    """返回 project_id."""
    print("=" * 60)
    print("Task 058b 运行前准备")
    print("=" * 60)

    # 1. 初始化数据库
    print("\n[1/4] 初始化数据库 schema...")
    await init_schema()
    print("   [OK] Schema 已初始化")

    # 2. 导入项目
    print("\n[2/4] 导入 scifi seed 项目...")
    project_id = await import_seed_project(SEED_CONFIG)
    print(f"   [OK] 项目已创建: {project_id}")

    # 3. 导入种子章节
    print("\n[3/4] 导入种子章节 Ch1...")
    version_id = await import_seed_chapter(project_id, SEED_CHAPTER, chapter_number=1)
    print(f"   [OK] Ch1 已导入: {version_id}")

    # 4. 导入角色初始状态
    print("\n[4/4] 导入角色初始状态...")
    await _import_seed_character_states(project_id, version_id)
    print("   [OK] 角色状态已导入")

    # 5. 验证
    print("\n" + "=" * 60)
    print("验证数据库状态")
    print("=" * 60)
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM projects WHERE project_id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        print(f"   项目存在: {row[0] == 1}")

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM chapter_versions WHERE project_id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        print(f"   章节版本数: {row[0]}")

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM summaries WHERE project_id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        print(f"   Summary 数: {row[0]}")

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM character_states WHERE source_version_id = ?",
            (version_id,),
        )
        row = await cursor.fetchone()
        print(f"   角色状态数: {row[0]}")

    print(f"\n[Done] 准备完成！project_id: {project_id}")
    return project_id


if __name__ == "__main__":
    pid = asyncio.run(main())
    print(f"\nexport PROJECT_ID={pid}")

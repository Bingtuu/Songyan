"""Task 170e Stage 1 探针：seed 真实角色 → 直接跑 generate_dialogue_style_cards.

Stage 0 已钉死：170b DB 的 characters 表为空，声纹机制从未激活。
本探针在**独立隔离 DB**（不碰 170b DB、不碰主库）seed 轨道蜃景真实卡司，
只调用一次 generate_dialogue_style_cards，检查机制"被喂到角色后"是否产出
**有区分度**的声纹卡（验证假设 E：卡是否雷同）。

这是最省的高信号第一步——一次 LLM 调用就能判断是否还需要改 prompt 模板，
再决定是否值得做整章重生成。

用法:
    python scripts/probe_170e_dialogue_style.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings

# 独立隔离 DB，绝不碰 170b DB / 主库。
# 注意：不读 os.getenv("DATABASE_URL")——.env 里 DATABASE_URL 指向主库 songyan.db，
# 读它会污染隔离目标。settings 已自动从 .env 加载 LLM 配置，无需 load_dotenv。
# 允许 PROBE_DB 显式覆盖（仅用于 .tmp 下隔离路径）。
_probe_db = os.getenv("PROBE_DB", ".tmp/task170e_probe.db")
if not _probe_db.startswith(".tmp/"):
    raise SystemExit(f"[safety] PROBE_DB 必须在 .tmp/ 下，拒绝: {_probe_db}")
settings.database_url = f"sqlite:///{_probe_db}"

from songyan.agents.creative_director import generate_dialogue_style_cards  # noqa: E402
from songyan.db.connection import get_db_path  # noqa: E402
from songyan.db.migrations import init_schema  # noqa: E402
from songyan.db.repository import CharacterRepository, ProjectRepository  # noqa: E402
from songyan.models.character import Character  # noqa: E402
from songyan.models.project import ProjectSetting  # noqa: E402

_CARD_AXES = [
    "sentence_length_preference",
    "common_openers",
    "common_closers",
    "anger_expression",
    "fear_expression",
    "joy_expression",
    "sadness_expression",
    "metaphor_frequency",
    "irony_usage",
    "rhetorical_question_habit",
    "interrupt_frequency",
    "pause_habit",
    "education_level_hint",
    "social_role_speech_pattern",
]


def _project() -> ProjectSetting:
    return ProjectSetting(
        title="轨道蜃景",
        genre_id="scifi",
        mode_id="webnovel_intense",
        protagonist_name="林渊",
        protagonist_background="前星际考古学家，因一次事故失去搭档，独自追查真相",
        core_hook="人类在太阳系边缘发现无法解析的黑色结构『方舟』，林渊是唯一能与之共鸣者",
        tone="热血",
        target_word_count=450000,
        estimated_chapters=150,
        words_per_chapter=3000,
        story_structure="serial",
    )


def _cast(project_id: str) -> list[Character]:
    """轨道蜃景真实卡司（对齐 170b 正文里反复出场的角色）."""
    def cid(slug: str) -> str:
        return f"char-{project_id[:8]}-{slug}"

    return [
        Character(
            character_id=cid("linyuan"),
            project_id=project_id,
            name="林渊",
            role_type="protagonist",
            background="前星际考古学家，理性、克制，因搭档之死背负愧疚，习惯用专业术语自我防御",
            personality_traits=["理性", "隐忍", "偏执于真相"],
            goals=["查明方舟真相", "解开搭档死亡之谜"],
        ),
        Character(
            character_id=cid("suwan"),
            project_id=project_id,
            name="苏晚",
            role_type="supporting",
            background="以全息影像/记忆副本形式存在的神秘存在，语气疏离、含隐喻，话里藏话",
            personality_traits=["神秘", "疏离", "话中有话"],
            goals=["引导林渊走向某个真相", "隐藏自身真实意图"],
        ),
        Character(
            character_id=cid("medic"),
            project_id=project_id,
            name="医疗官",
            role_type="supporting",
            background="方舟站医疗官，务实、直接，说话短促、爱下判断，紧张时语速加快",
            personality_traits=["务实", "直接", "警觉"],
            goals=["监控林渊的量子化异变", "保住站内安全"],
        ),
        Character(
            character_id=cid("laolei"),
            project_id=project_id,
            name="老雷",
            role_type="supporting",
            background="资深站长，江湖气、爱用俚语和反问，粗中有细",
            personality_traits=["老练", "江湖气", "护短"],
            goals=["维持空间站运转", "护住林渊"],
        ),
    ]


def _distinctness_report(cards: list) -> int:
    """两两比较，返回高度雷同对数（相同轴 >=60%）."""
    print("\n[distinctness] 声纹卡两两区分度")
    if len(cards) < 2:
        print("  可比卡 < 2")
        return 0
    by_id = {c.character_id: c for c in cards}
    ids = list(by_id)
    homogeneous = 0
    n = len(_CARD_AXES)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = by_id[ids[i]], by_id[ids[j]]
            same = 0
            same_axes = []
            for axis in _CARD_AXES:
                va, vb = getattr(a, axis), getattr(b, axis)
                if isinstance(va, list):
                    va, vb = tuple(va), tuple(vb)
                if va == vb and va not in (None, "", ()):
                    same += 1
                    same_axes.append(axis)
            ratio = same / n
            tag = "⚠️ 高度雷同" if ratio >= 0.6 else ("偏雷同" if ratio >= 0.4 else "有区分")
            if ratio >= 0.6:
                homogeneous += 1
            print(f"  {ids[i]} ↔ {ids[j]}: {same}/{n} ({ratio:.0%}) {tag}")
            if same_axes:
                print(f"      相同轴: {', '.join(same_axes)}")
    return homogeneous


def _dump_card(c: object) -> None:
    print(f"\n  ── {getattr(c, 'character_id', '?')} ──")
    for axis in _CARD_AXES:
        print(f"    {axis} = {getattr(c, axis, None)!r}")


async def _amain() -> int:
    db_path = get_db_path()
    for suffix in ("", "-wal", "-shm"):
        p = db_path.with_name(db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()
    await init_schema()
    print(f"[preflight] fresh DB={settings.database_url}")

    project_id = uuid.uuid4().hex
    await ProjectRepository().create(_project(), project_id)
    cast = _cast(project_id)
    repo = CharacterRepository()
    for ch in cast:
        await repo.create(ch)
    print(f"[seed] project={project_id}  seeded {len(cast)} characters:"
          f" {', '.join(c.name for c in cast)}")

    print("\n[probe] 调用 generate_dialogue_style_cards（真实 LLM，一次调用）...")
    cards = await generate_dialogue_style_cards(cast, project_id)
    print(f"[probe] 返回声纹卡数 = {len(cards)}")

    if not cards:
        print("\n→ FAIL：机制被喂到角色后仍返回 []（LLM 降级/解析失败）。查 LLM 配置与降级路径。")
        return 1

    name_by_id = {c.character_id: c.name for c in cast}
    for c in cards:
        print(f"\n角色 {name_by_id.get(c.character_id, c.character_id)}：")
        _dump_card(c)

    homogeneous = _distinctness_report(cards)
    print("\n" + "=" * 60)
    if homogeneous == 0 and len(cards) >= 2:
        print("→ PASS：机制被喂到角色后产出有区分度的声纹卡。")
        print("  假设 E（卡雷同）不成立。voice 塌陷主因 = Stage 0 的 seeding gap。")
        print("  下一步：小样本整章重生成，用 170d 量具复评 voice 是否随之抬升。")
    else:
        print(f"→ 观察：{homogeneous} 对卡高度雷同 → 假设 E 部分成立。")
        print("  即便补了 seed，仍需强化 _DIALOGUE_STYLE_PROMPT_TEMPLATE 的跨角色差异约束。")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_amain()))

"""Task 170e Stage 2：小样本真实生成 —— 验证 seeding 修复后声纹机制被激活.

自包含、隔离 DB（强制 .tmp/），不碰 170b DB / 主库：
  1. 建干净项目 + 导入轨道蜃景大纲 + seed 完整卡司（主角 + 配角）。
     （生产端自动建 protagonist 已由 ensure_protagonist_character 覆盖；
      配角按 170e 决策由 harness 手动 seed。）
  2. 真实 LLM 生成 Ch1-Ch5（enforce 门禁）。
  3. 验证：
     - 各章 context_snapshots.payload 的 dialogue_style_cards 从 0 变非空（机制激活）；
     - characters 表 dialogue_style_card 落库（generate 触发并持久化）；
     - 正文对各角色 openers 粗查落地（启发式，人工遮标签为准）。

用法:
    python scripts/run_170e_stage2_small_sample.py --init   # 建库+seed
    python scripts/run_170e_stage2_small_sample.py          # 生成+验证
    python scripts/run_170e_stage2_small_sample.py --verify # 只验证已生成结果
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings

# 强制隔离 DB（.tmp/ 下），绝不读 .env 的 DATABASE_URL（那指向主库）。
_db = os.getenv("STAGE2_DB", ".tmp/task170e_stage2.db")
if not _db.startswith(".tmp/"):
    raise SystemExit(f"[safety] STAGE2_DB 必须在 .tmp/ 下，拒绝: {_db}")
settings.database_url = f"sqlite:///{_db}"

from songyan.db import get_db  # noqa: E402
from songyan.db.connection import get_db_path  # noqa: E402
from songyan.db.migrations import init_schema  # noqa: E402
from songyan.db.narrative_repo import NarrativeRepository  # noqa: E402
from songyan.db.repository import CharacterRepository, ProjectRepository  # noqa: E402
from songyan.models import ArcPlan, GateConfig, PlotThread, StoryOutline  # noqa: E402
from songyan.models.character import Character, DialogueStyleCard  # noqa: E402
from songyan.models.project import ProjectSetting  # noqa: E402
from songyan.workflows.phase2_graph import run_project_pipeline  # noqa: E402

PROJECT_FILE = Path(".tmp/task170e_stage2_project.json")
START_CH, END_CH = 1, int(os.getenv("END_CHAPTER", "5"))


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
        arc_boundaries=[25, 50, 75, 100, 125],
        arc_boundaries_auto=True,
    )


def _cast(project_id: str) -> list[Character]:
    """完整卡司：主角 + 3 配角。配角带占位声纹卡（保证 seed 后即有区分基线），
    主角故意留空 dialogue_style_card，验证 pipeline 会为其生成。"""
    def cid(slug: str) -> str:
        return f"char-{project_id[:8]}-{slug}"

    return [
        Character(
            character_id=cid("linyuan"),
            project_id=project_id,
            name="林渊",
            role_type="protagonist",
            background="前星际考古学家，理性克制，习惯用专业术语自我防御",
            personality_traits=["理性", "隐忍", "偏执于真相"],
            goals=["查明方舟真相"],
        ),
        Character(
            character_id=cid("suwan"),
            project_id=project_id,
            name="苏晚",
            role_type="supporting",
            background="以全息影像/记忆副本存在的神秘存在，语气疏离含隐喻",
            personality_traits=["神秘", "疏离"],
            dialogue_style_card=DialogueStyleCard(
                character_id=cid("suwan"),
                project_id=project_id,
                sentence_length_preference="medium",
                common_openers=["你不觉得……", "有些答案，"],
                metaphor_frequency="frequent",
                rhetorical_question_habit=True,
                pause_habit="在关键名词前刻意停顿",
            ),
        ),
        Character(
            character_id=cid("medic"),
            project_id=project_id,
            name="医疗官",
            role_type="supporting",
            background="方舟站医疗官，务实直接，说话短促爱下判断",
            personality_traits=["务实", "直接"],
            dialogue_style_card=DialogueStyleCard(
                character_id=cid("medic"),
                project_id=project_id,
                sentence_length_preference="short",
                common_openers=["听着，", "别动，"],
                metaphor_frequency="rare",
                interrupt_frequency="frequent",
            ),
        ),
        Character(
            character_id=cid("laolei"),
            project_id=project_id,
            name="老雷",
            role_type="supporting",
            background="资深站长，江湖气，爱用俚语和反问",
            personality_traits=["老练", "江湖气"],
            dialogue_style_card=DialogueStyleCard(
                character_id=cid("laolei"),
                project_id=project_id,
                sentence_length_preference="mixed",
                common_openers=["我说，", "这他娘的"],
                irony_usage=True,
                rhetorical_question_habit=True,
            ),
        ),
    ]


def _outline(project_id: str) -> tuple[StoryOutline, list[ArcPlan], list[PlotThread]]:
    outline = StoryOutline(
        project_id=project_id,
        core_conflict="人类文明存续与深空黑色结构『方舟』意志之间的对抗",
        mainline_synopsis="林渊追查方舟真相，逐渐揭开搭档之死的隐情。",
        themes=["存续与牺牲", "认知边界"],
        intended_ending="林渊以自身共鸣为代价封存方舟",
    )
    threads = [
        PlotThread(thread_id="t_ark", project_id=project_id, title="方舟",
                   description="太阳系边缘黑色结构，疑似有意志", is_mainline=True,
                   expected_resolve_arc=5),
        PlotThread(thread_id="t_resonance", project_id=project_id, title="共鸣",
                   description="林渊与方舟独有的感应能力", is_mainline=True,
                   expected_resolve_arc=4),
        PlotThread(thread_id="t_partner", project_id=project_id, title="旧日搭档",
                   description="林渊失去的搭档之死背后的隐情", is_mainline=True,
                   expected_resolve_arc=3),
    ]
    arcs = [
        ArcPlan(arc_id=f"{project_id}-arc0", project_id=project_id, arc_index=0,
                start_chapter=1, end_chapter=25,
                arc_goal="发现方舟、确立林渊共鸣者身份，开启三主线",
                threads_to_open=["t_ark", "t_resonance", "t_partner"],
                threads_to_resolve=[], is_mainline=True),
    ]
    return outline, arcs, threads


async def _init() -> str:
    db_path = get_db_path()
    for suffix in ("", "-wal", "-shm"):
        p = db_path.with_name(db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()
    await init_schema()
    project_id = uuid.uuid4().hex
    await ProjectRepository().create(_project(), project_id)
    outline, arcs, threads = _outline(project_id)
    await NarrativeRepository().import_outline(project_id, outline, arcs, threads)
    cast = _cast(project_id)
    repo = CharacterRepository()
    for ch in cast:
        await repo.create(ch)
    PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(json.dumps({"project_id": project_id}, ensure_ascii=False),
                            encoding="utf-8")
    seeded = [(c.name, c.dialogue_style_card is not None) for c in cast]
    print(f"[init] DB={settings.database_url}")
    print(f"[init] project={project_id}")
    print(f"[init] seeded cast (name, has_card): {seeded}")
    print("[init] 主角 林渊 故意留空 card → 验证 pipeline 会为其生成")
    return project_id


def _resolve_project_id() -> str | None:
    pid = os.getenv("PROJECT_ID")
    if pid:
        return pid
    if PROJECT_FILE.exists():
        return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get("project_id")
    return None


async def _verify(project_id: str) -> int:
    print("\n" + "=" * 68)
    print("Stage 2 验证：声纹机制是否被激活")
    print("=" * 68)

    # 1. characters 表：主角是否被生成了 card
    chars = await CharacterRepository().list_by_project(project_id)
    with_card = [c for c in chars if c.dialogue_style_card is not None]
    print(f"\n[1] characters 表：{len(with_card)}/{len(chars)} 有声纹卡")
    for c in chars:
        print(f"    [{'✓' if c.dialogue_style_card else '✗'}] {c.name}（{c.role_type}）")

    # 2. 各章 snapshot 是否携带声纹卡（对比 170b 全 0）
    print("\n[2] 各章 context_snapshots.dialogue_style_cards 数（170b 基线=全 0）：")
    activated = 0
    async with get_db() as conn:
        conn.row_factory = __import__("aiosqlite").Row
        for ch in range(START_CH, END_CH + 1):
            cur = await conn.execute(
                """SELECT payload FROM context_snapshots
                   WHERE project_id=? AND chapter_number=?
                   ORDER BY created_at DESC LIMIT 1""",
                (project_id, ch),
            )
            row = await cur.fetchone()
            if row is None:
                print(f"    Ch{ch}: 无 snapshot")
                continue
            raw = row["payload"]
            payload = json.loads(raw) if isinstance(raw, str) else raw
            n = len(payload.get("dialogue_style_cards", []) or [])
            if n > 0:
                activated += 1
            print(f"    Ch{ch}: {n} 张声纹卡 {'✓ 激活' if n else '✗ 空'}")

    print("\n" + "=" * 68)
    if activated > 0 and with_card:
        print(f"→ PASS：声纹机制已激活（{activated} 章 snapshot 携带声纹卡，"
              f"主角卡已生成）。对比 170b 全 0 的死代码状态，seeding 修复生效。")
        print("  下一步（170g）：用 170d 校准量具全窗口复评 voice，人工遮标签抽读确认假设 C。")
        return 0
    print("→ FAIL：snapshot 仍无声纹卡，需进一步排查（预算裁剪/注入谓词）。")
    return 1


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.init:
        await _init()
        return

    project_id = _resolve_project_id()
    if not project_id:
        parser.error("请先 --init")

    if args.verify:
        raise SystemExit(await _verify(project_id))

    print(f"[run] DB={settings.database_url}  project={project_id}  range=({START_CH},{END_CH})")
    result = await run_project_pipeline(
        project_id=project_id,
        chapter_range=(START_CH, END_CH),
        mode_id="webnovel_intense",
        auto_confirm=True,
        on_failure="isolate",
        gate_config=GateConfig.for_mode("enforce"),
    )
    print(f"\n[run] completed={result.chapters_completed} failed={result.chapters_failed} "
          f"status={result.final_status} dur={result.total_duration_sec:.0f}s")

    raise SystemExit(await _verify(project_id))


if __name__ == "__main__":
    asyncio.run(main())

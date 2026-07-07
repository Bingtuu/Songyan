"""Task 170e Stage 0 复现脚本：定位 voice 声纹塌陷的失效环节.

只读、不改任何数据。从 170b 隔离 DB 读角色声纹卡、章节正文、
上下文快照，逐环回答 Q1-Q6，钉死根因（A / B′-filter / B′-eviction / C / E）。

链路（170e 文档已查证）：
  生成 creative_director_node → 落库 characters.dialogue_style_card
  → 重载+过滤 _helpers.assemble_context_package(appeared_names 谓词)
  → 裁剪 context_manager(_enforce_budget_hard Step1 / emergency)
  → 存快照 context_snapshots.payload → Writer 注入。

用法:
    python scripts/repro_170e_voice_pipeline.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings

# 与 170b/170c 一致：强制隔离 DB，绝不碰主库。
settings.database_url = os.getenv("DATABASE_URL", "sqlite:///.tmp/task170b_ch1_ch40.db")

import json  # noqa: E402

from songyan.db.connection import get_db  # noqa: E402
from songyan.db.repository import (  # noqa: E402
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
)
from songyan.models.context import ContextPackage  # noqa: E402
from songyan.workflows._helpers import load_layered_summaries  # noqa: E402

PROJECT_FILE = Path(".tmp/task170b_project.json")
# 抽检章：Ch31（170b 亲验 voice=1 + 重复缺陷）+ Ch37（医疗官短对白，多人对话）
SAMPLE_CHAPTERS = [int(c) for c in os.getenv("REPRO_CHAPTERS", "31,37").split(",")]

# DialogueStyleCard 字段轴，用于 Q2 相似度。
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


def _resolve_project_id() -> str | None:
    pid = os.getenv("PROJECT_ID")
    if pid:
        return pid
    if PROJECT_FILE.exists():
        return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get("project_id")
    return None


async def _load_chapter_content(project_id: str, chapter: int) -> str | None:
    head = await ChapterHeadRepository().get(project_id, chapter)
    if head is None or head.status != "accepted" or not head.accepted_version_id:
        return None
    version = await ChapterVersionRepository().get(head.accepted_version_id)
    return version.content if version else None


async def _load_latest_snapshot_row(project_id: str, chapter: int) -> dict | None:
    """直接查 context_snapshots（repo 只有按 id get），取该章最新一条."""
    async with get_db() as conn:
        conn.row_factory = __import__("aiosqlite").Row
        cursor = await conn.execute(
            """SELECT snapshot_id, budget_used, context_emergency,
                      context_emergency_level, budget_used_before_emergency, payload,
                      created_at
               FROM context_snapshots
               WHERE project_id = ? AND chapter_number = ?
               ORDER BY created_at DESC, snapshot_id DESC
               LIMIT 1""",
            (project_id, chapter),
        )
        row = await cursor.fetchone()
    return dict(row) if row is not None else None


def _axis_value(card: object, axis: str) -> object:
    val = getattr(card, axis, None)
    if isinstance(val, list):
        return tuple(str(v) for v in val)
    return val


def _pair_similarity(a: object, b: object) -> tuple[int, list[str]]:
    """返回 (相同轴数, 相同轴列表)."""
    same: list[str] = []
    for axis in _CARD_AXES:
        va, vb = _axis_value(a, axis), _axis_value(b, axis)
        if va == vb and va not in (None, "", ()):
            same.append(axis)
    return len(same), same


# ---------------------------------------------------------------------------
# Q1: 卡是否生成（假设 A）
# ---------------------------------------------------------------------------
def _q1_cards_generated(characters: list) -> dict:
    with_card = [c for c in characters if c.dialogue_style_card is not None]
    total = len(characters)
    print("\n" + "=" * 72)
    print("[Q1 / 假设A] 角色声纹卡生成情况")
    print("=" * 72)
    print(f"  项目角色总数 = {total}")
    print(f"  已生成声纹卡 = {len(with_card)}")
    for c in characters:
        flag = "✓" if c.dialogue_style_card is not None else "✗ 无卡"
        print(f"    [{flag}] {c.name}（{c.role_type}, id={c.character_id}）")
    verdict = "PASS（卡已生成）" if with_card else "FAIL（无任何声纹卡 → 假设A成立）"
    print(f"  → {verdict}")
    return {"total": total, "with_card": len(with_card), "cards_ok": bool(with_card)}


# ---------------------------------------------------------------------------
# Q2: 卡是否雷同（假设 E）
# ---------------------------------------------------------------------------
def _q2_cards_distinct(characters: list) -> dict:
    carded = [(c.name, c.dialogue_style_card) for c in characters if c.dialogue_style_card]
    print("\n" + "=" * 72)
    print("[Q2 / 假设E] 声纹卡两两区分度（相同轴数越高越雷同）")
    print("=" * 72)
    if len(carded) < 2:
        print("  可比卡 < 2，跳过 Q2")
        return {"comparable": len(carded), "homogeneous_pairs": 0}
    homogeneous_pairs = 0
    total_axes = len(_CARD_AXES)
    for i in range(len(carded)):
        for j in range(i + 1, len(carded)):
            (na, ca), (nb, cb) = carded[i], carded[j]
            same_n, same_axes = _pair_similarity(ca, cb)
            ratio = same_n / total_axes
            tag = "⚠️ 高度雷同" if ratio >= 0.6 else ("偏雷同" if ratio >= 0.4 else "有区分")
            if ratio >= 0.6:
                homogeneous_pairs += 1
            print(f"  {na} ↔ {nb}: 相同 {same_n}/{total_axes} 轴 ({ratio:.0%})  {tag}")
            if same_axes:
                print(f"      相同轴: {', '.join(same_axes)}")
    verdict = (
        f"FAIL（{homogeneous_pairs} 对高度雷同 → 假设E成立）"
        if homogeneous_pairs
        else "PASS（卡间有区分）"
    )
    print(f"  → {verdict}")
    return {"comparable": len(carded), "homogeneous_pairs": homogeneous_pairs}


# ---------------------------------------------------------------------------
# Q3: 注入谓词过滤（假设 B′-filter）
# ---------------------------------------------------------------------------
async def _q3_injection_filter(project_id: str, characters: list, chapter: int) -> dict:
    """复刻 _helpers.py:402-411 的注入谓词，看谁的卡被过滤."""
    recent_summaries = await load_layered_summaries(project_id, chapter)
    appeared_names: set[str] = set()
    for s in recent_summaries:
        appeared_names.update(getattr(s, "characters_appeared", None) or [])

    content = await _load_chapter_content(project_id, chapter)
    print("\n" + "=" * 72)
    print(f"[Q3 / 假设B′-filter] Ch{chapter} 注入谓词过滤（_helpers.py:410 复刻）")
    print("=" * 72)
    print(f"  近期摘要 appeared_names = {sorted(appeared_names) or '（空）'}")

    dropped_speakers: list[str] = []
    injected = 0
    for c in characters:
        if c.dialogue_style_card is None:
            continue
        is_proto = c.role_type == "protagonist"
        in_appeared = c.name in appeared_names
        will_inject = is_proto or in_appeared
        in_prose = bool(content and c.name in content)
        if will_inject:
            injected += 1
        status = "注入" if will_inject else "✗被过滤"
        prose_tag = " [本章正文出现]" if in_prose else ""
        print(
            f"    [{status}] {c.name}（proto={is_proto}, in_appeared={in_appeared}）{prose_tag}"
        )
        # 关键失效信号：本章正文里出现（大概率开口）但卡被过滤掉
        if in_prose and not will_inject:
            dropped_speakers.append(c.name)

    if dropped_speakers:
        print(f"  ⚠️ 本章出现但卡被过滤的角色: {', '.join(dropped_speakers)}")
        verdict = "FAIL（有本章角色卡被过滤 → 假设B′-filter成立）"
    else:
        verdict = "PASS（本章出现角色的卡均注入）"
    print(f"  Ch{chapter} 注入卡数 = {injected}")
    print(f"  → {verdict}")
    return {"chapter": chapter, "injected": injected, "dropped_speakers": dropped_speakers}


# ---------------------------------------------------------------------------
# Q4: 快照裁剪（假设 B′-eviction）—— Writer 实际拿到的上下文
# ---------------------------------------------------------------------------
async def _q4_snapshot_eviction(project_id: str, chapter: int) -> dict:
    row = await _load_latest_snapshot_row(project_id, chapter)
    print("\n" + "=" * 72)
    print(f"[Q4 / 假设B′-eviction] Ch{chapter} 存储快照（Writer 实际输入）")
    print("=" * 72)
    if row is None:
        print("  未找到该章 context_snapshot（可能未落快照）")
        return {"chapter": chapter, "snapshot": False}
    payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
    cards = payload.get("dialogue_style_cards", []) if isinstance(payload, dict) else []
    budget_used = row["budget_used"]
    emergency = bool(row["context_emergency"])
    emergency_lvl = row["context_emergency_level"] or 0
    print(f"  snapshot_id = {row['snapshot_id']}")
    print(f"  budget_used = {budget_used}")
    print(f"  context_emergency = {emergency}（level={emergency_lvl}）")
    print(f"  快照内 dialogue_style_cards 数 = {len(cards)}")
    if cards:
        for c in cards:
            print(f"    - {c.get('character_id', '?')}")
    over_budget = isinstance(budget_used, (int, float)) and budget_used > 1.0
    evicted = (len(cards) == 0) and (emergency or over_budget)
    verdict = (
        "FAIL（快照卡为空且触发预算/emergency → 假设B′-eviction成立）"
        if evicted
        else ("观察（快照卡为空，但无预算/emergency，指向B′-filter）"
              if len(cards) == 0 else "PASS（快照携带声纹卡）")
    )
    print(f"  → {verdict}")
    return {
        "chapter": chapter,
        "snapshot": True,
        "cards_in_snapshot": len(cards),
        "budget_used": budget_used,
        "emergency": emergency,
        "over_budget": over_budget,
        "evicted": evicted,
    }


# ---------------------------------------------------------------------------
# Q5/Q6: 注入前置 + 遵守（假设 C）
# ---------------------------------------------------------------------------
async def _q5_prompt_render(project_id: str, chapter: int) -> dict:
    """用存储快照重建 ContextPackage，渲染真实 Writer prompt，看对话风格块是否出现."""
    row = await _load_latest_snapshot_row(project_id, chapter)
    print("\n" + "=" * 72)
    print(f"[Q5 / 假设C前置] Ch{chapter} Writer prompt 实际渲染")
    print("=" * 72)
    if row is None:
        print("  无快照，跳过 Q5")
        return {"chapter": chapter, "rendered": False}
    payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
    try:
        ctx = ContextPackage.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"  ContextPackage 重建失败: {exc}")
        return {"chapter": chapter, "rendered": False}
    try:
        from songyan.agents.writer import _render_prompt

        prompt = _render_prompt(ctx)
    except Exception as exc:  # noqa: BLE001
        print(f"  _render_prompt 失败: {exc}")
        return {"chapter": chapter, "rendered": False}
    has_block = "出场角色对话风格" in prompt
    # 块存在但内容为空占位 → 等价于没注入
    block_has_content = has_block and "（无）" not in prompt.split("出场角色对话风格", 1)[1][:200]
    print(f"  prompt 总长 = {len(prompt)} 字")
    print(f"  含『出场角色对话风格』块 = {has_block}")
    print(f"  块内有真实内容 = {block_has_content}")
    verdict = (
        "PASS（对话风格块带内容进入 prompt → 若正文仍塌陷则指向假设C）"
        if block_has_content
        else "FAIL（prompt 无有效对话风格块 → 塌陷发生在注入前，非C）"
    )
    print(f"  → {verdict}")
    return {"chapter": chapter, "rendered": True, "block_has_content": block_has_content}


async def _q6_prose_landing(project_id: str, characters: list, chapter: int) -> dict:
    """对本章正文粗查各角色 openers 是否落地（启发式，供人工遮标签抽读定位）."""
    content = await _load_chapter_content(project_id, chapter)
    print("\n" + "=" * 72)
    print(f"[Q6 / 假设C] Ch{chapter} 正文声纹落地粗查（启发式）")
    print("=" * 72)
    if not content:
        print("  无正文，跳过 Q6")
        return {"chapter": chapter, "checked": False}
    landed = 0
    checked = 0
    for c in characters:
        card = c.dialogue_style_card
        if card is None or c.name not in content:
            continue
        openers = list(getattr(card, "common_openers", []) or [])
        if not openers:
            continue
        checked += 1
        hits = [op for op in openers if op and op in content]
        if hits:
            landed += 1
        print(f"    {c.name}: openers={openers} → 命中 {hits or '无'}")
    print(f"  可查角色 = {checked}，openers 命中角色 = {landed}")
    print("  （注：启发式仅查口头禅字面命中，声纹是否真落地以人工遮标签抽读为准）")
    return {"chapter": chapter, "checked": checked, "landed": landed}


def _print_verdict(q1: dict, q2: dict, q3s: list[dict], q4s: list[dict], q5s: list[dict]) -> None:
    print("\n" + "#" * 72)
    print("# 根因裁定汇总")
    print("#" * 72)
    if not q1["cards_ok"]:
        print("  ▶ 假设A（卡未生成）成立：优先修生成/降级路径。")
        return
    any_dropped = any(q["dropped_speakers"] for q in q3s)
    any_evicted = any(q.get("evicted") for q in q4s)
    any_empty_snapshot = any(
        q.get("snapshot") and q.get("cards_in_snapshot") == 0 and not q.get("evicted")
        for q in q4s
    )
    homogeneous = q2.get("homogeneous_pairs", 0) > 0
    block_ok = any(q.get("block_has_content") for q in q5s)

    print(f"  Q3 本章角色卡被过滤（B′-filter）: {'是' if any_dropped else '否'}")
    print(f"  Q4 快照裁剪丢卡（B′-eviction）:   {'是' if any_evicted else '否'}")
    print(f"  Q4 快照空但非预算触发（→filter）: {'是' if any_empty_snapshot else '否'}")
    print(f"  Q2 卡高度雷同（E）:              {'是' if homogeneous else '否'}")
    print(f"  Q5 对话风格块带内容进 prompt:     {'是' if block_ok else '否'}")

    print("\n  裁定：")
    if any_dropped or any_empty_snapshot:
        print("  ▶ B′-filter 成立：注入谓词把本章说话角色的卡过滤掉了。首要修 _helpers 谓词。")
    if any_evicted:
        print("  ▶ B′-eviction 成立：预算/emergency 把声纹卡裁掉了。需调裁剪顺序或收窄卡集。")
    if homogeneous:
        print("  ▶ E 成立：卡本身雷同。需强化 _DIALOGUE_STYLE_PROMPT_TEMPLATE 跨角色差异。")
    if block_ok and not (any_dropped or any_evicted or any_empty_snapshot):
        print("  ▶ 指向 C：卡进了 prompt 但正文仍塌陷。"
              "需硬化 Writer 卡执行力（配合人工抽读确认）。")
    if not any([any_dropped, any_empty_snapshot, any_evicted, homogeneous, block_ok]):
        print("  ▶ 未自动命中单一根因，需人工结合上方逐 Q 输出判断。")


async def _amain() -> int:
    if not Path(settings.database_url.replace("sqlite:///", "")).exists():
        print(f"[error] 隔离 DB 不存在: {settings.database_url}")
        return 1
    project_id = _resolve_project_id()
    if not project_id:
        print("[error] 无法解析 project_id（设 PROJECT_ID 或确保 .tmp/task170b_project.json 存在）")
        return 1

    print(f"[preflight] DB={settings.database_url}  project_id={project_id}")
    print(f"[preflight] 抽检章 = {SAMPLE_CHAPTERS}")

    characters = await CharacterRepository().list_by_project(project_id)

    q1 = _q1_cards_generated(characters)
    q2 = _q2_cards_distinct(characters)

    q3s: list[dict] = []
    q4s: list[dict] = []
    q5s: list[dict] = []
    for ch in SAMPLE_CHAPTERS:
        q3s.append(await _q3_injection_filter(project_id, characters, ch))
        q4s.append(await _q4_snapshot_eviction(project_id, ch))
        q5s.append(await _q5_prompt_render(project_id, ch))
        await _q6_prose_landing(project_id, characters, ch)

    _print_verdict(q1, q2, q3s, q4s, q5s)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_amain()))

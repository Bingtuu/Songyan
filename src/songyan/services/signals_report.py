"""task 257：S 信号聚合（tech-post-m4 v2 §B.2）。

每信号注明数据源 → PRD §5.2 口径映射。拿不到口径所需数据的信号显式标
``gap``，不编造。当前进度章 = 最大 accepted 章（chapter_heads）。
"""

from __future__ import annotations

from statistics import median
from typing import Any

from songyan.db.connection import get_db

_PLAN_TABLES = {
    "entities": ("plan_entities", "entity_id"),
    "attributes": ("plan_attributes", "attribute_id"),
    "events": ("plan_events", "event_id"),
    "clues": ("plan_clues", "clue_id"),
    "time_anchors": ("plan_time_anchors", "anchor_id"),
}


async def _current_progress_chapter(project_id: str) -> int:
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COALESCE(MAX(chapter_number), 0) FROM chapter_heads "
            "WHERE project_id = ? AND accepted_version_id IS NOT NULL",
            (project_id,),
        )
        row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def _s1(project_id: str) -> dict[str, Any]:
    """S1 周确认数 + dismiss 比。

    数据源：plan_* 五表。局限：updated_at 落在窗口且 approved 计数包含窗口内
    的编辑触碰，非纯 confirm 动作（现网无动作记账面）——note 注明。
    dismiss 比 = rejected/(approved+rejected) 全量。
    """
    weekly = 0
    approved = 0
    rejected = 0
    async with get_db() as conn:
        for table, _id_col in _PLAN_TABLES.values():
            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE project_id = ? "
                "AND approval_status = 'approved' "
                "AND updated_at >= datetime('now', '-7 days')",
                (project_id,),
            )
            weekly += (await cursor.fetchone())[0]
            cursor = await conn.execute(
                f"SELECT "
                "SUM(CASE WHEN approval_status='approved' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN approval_status='rejected' THEN 1 ELSE 0 END) "
                f"FROM {table} WHERE project_id = ?",
                (project_id,),
            )
            row = await cursor.fetchone()
            approved += row[0] or 0
            rejected += row[1] or 0
    total = approved + rejected
    return {
        "weekly_confirms": weekly,
        "dismiss_ratio": round(rejected / total, 4) if total else 0.0,
        "note": "周计数含窗口内编辑触碰（无动作记账面）；dismiss 比为全量口径",
    }


async def _s3(project_id: str) -> dict[str, Any]:
    """S3 开放伏笔年龄 P50（未 resolved：planted/due/overdue；负年龄 clamp 0）。"""
    current = await _current_progress_chapter(project_id)
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT planted_in_chapter FROM foreshadowings "
            "WHERE project_id = ? AND lifecycle_status = 'active' "
            "AND status IN ('planted', 'due', 'overdue')",
            (project_id,),
        )
        rows = await cursor.fetchall()
    ages = sorted(max(0, current - int(r[0])) for r in rows)
    return {
        "open_count": len(ages),
        "age_p50": median(ages) if ages else 0,
        "current_chapter": current,
    }


async def _s4(project_id: str) -> dict[str, Any]:
    """S4 抽卡采纳分布；全 pick 1 号给塌缩提示（PRD：先查塌缩，不加 N）。"""
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT slot_index, COUNT(*) FROM chapter_variants "
            "WHERE project_id = ? AND status = 'picked' GROUP BY slot_index",
            (project_id,),
        )
        rows = await cursor.fetchall()
    slots = {str(r[0]): int(r[1]) for r in rows}
    total = sum(slots.values())
    return {
        "picks_total": total,
        "slots": slots,
        "collapse_warning": bool(total > 1 and set(slots) == {"1"}),
    }


async def _s5(project_id: str) -> dict[str, Any]:
    """S5 人改率分布（chapter_heads.edit_ratio 列；NULL = 未记，单列口径）。"""
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT edit_ratio FROM chapter_heads "
            "WHERE project_id = ? AND accepted_version_id IS NOT NULL",
            (project_id,),
        )
        rows = [r[0] for r in await cursor.fetchall()]
    values = [float(v) for v in rows if v is not None]
    low = sum(1 for v in values if v < 0.05)
    return {
        "count": len(values),
        "null_count": len(rows) - len(values),
        "mean": round(sum(values) / len(values), 4) if values else 0.0,
        "low_edit_share": round(low / len(values), 4) if values else 0.0,
        "note": "NULL = 列引入前（task 257 之前）的 accepted 章，未记",
    }


async def _s7(project_id: str) -> dict[str, Any]:
    """S7 单章成本：llm_call_usage 全项目合计 + settled 章数（口径为估算值）。"""
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(cost_cny), 0.0), COUNT(DISTINCT chapter_number) "
            "FROM llm_call_usage WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM chapter_heads "
            "WHERE project_id = ? AND accepted_version_id IS NOT NULL",
            (project_id,),
        )
        settled = (await cursor.fetchone())[0]
    return {
        "total_cost_cny": round(float(row[0]), 4),
        "chapters_with_usage": int(row[1] or 0),
        "settled_chapters": int(settled or 0),
        "note": "口径 ¥2/M 输入 ¥8/M 输出，是估算不是账单（PRD §5.2）",
    }


async def build_signals(project_id: str) -> dict[str, Any]:
    """组装 S1–S7（S2 gap 明示）。只读，零写库。"""
    return {
        "project_id": project_id,
        "signals": {
            "S1": await _s1(project_id),
            "S2": {
                "gap": True,
                "note": "冲突关闭周期需 open→closed/dismiss 时间记账面，现网无；立项另议",
            },
            "S3": await _s3(project_id),
            "S4": await _s4(project_id),
            "S5": await _s5(project_id),
            "S7": await _s7(project_id),
        },
    }

"""task 269 切片1：pending 提案分组过滤（纯函数）。

口径：
- attribute 匹配：--chapter → valid_from_ch == N（None 不属任何章）；
  --source → source 精确匹配；--kind → 只留 entity / attribute 一类。
- 任一过滤生效时，entity 入选条件 = 被过滤后 attribute 集按 entity_id 引用。
  未过滤 → entity 全集（保持 task 259 行为）。
理由：plan_entities 无章/来源列，extract 提案的新实体经本章 attribute 挂靠归组。
"""

from __future__ import annotations

from typing import Literal

from songyan.models.plan_facts import PlanAttribute, PlanEntity

PendingKind = Literal["entity", "attribute"]


def filter_pending(
    entities: list[PlanEntity],
    attributes: list[PlanAttribute],
    *,
    chapter: int | None = None,
    source: str | None = None,
    kind: PendingKind | None = None,
) -> tuple[list[PlanEntity], list[PlanAttribute]]:
    """按章/来源/类过滤 pending 集；返回 (entities, attributes)。"""
    if kind == "entity":
        attrs_out: list[PlanAttribute] = []
    else:
        attrs_out = [
            a
            for a in attributes
            if (chapter is None or a.valid_from_ch == chapter)
            and (source is None or a.source == source)
        ]
    if kind == "attribute":
        return [], attrs_out
    if chapter is None and source is None:
        return list(entities), attrs_out
    referenced = {a.entity_id for a in attrs_out}
    return [e for e in entities if e.entity_id in referenced], attrs_out

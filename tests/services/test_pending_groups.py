"""task 269 切片1：pending 分组过滤纯函数。

口径（写进测试钉死）：
- attribute 过滤：--chapter 匹配 valid_from_ch == N（None 不属任何章）；
  --source 匹配 source；--kind 只留一类。
- 任一过滤生效时，entity 入选条件 = 被过滤后的 attribute 集引用（entity_id）。
  未过滤时 entity 全集（保持 259 行为）。
- 空集合法：调用方 exit 0 明示。
"""

from __future__ import annotations

from songyan.models.plan_facts import PlanAttribute, PlanEntity
from songyan.services.pending_groups import filter_pending


def _entity(eid: str) -> PlanEntity:
    return PlanEntity(
        entity_id=eid,
        project_id="p1",
        entity_type="person",
        approval_status="pending",
    )


def _attr(aid: str, eid: str, from_ch: int | None, source: str = "human") -> PlanAttribute:
    return PlanAttribute(
        attribute_id=aid,
        project_id="p1",
        entity_id=eid,
        key="k",
        value="v",
        valid_from_ch=from_ch,
        source=source,  # type: ignore[arg-type]
        approval_status="pending",
    )


class TestChapterFilter:
    def test_chapter_matches_valid_from_ch(self) -> None:
        entities = [_entity("e1"), _entity("e2"), _entity("e3")]
        attrs = [
            _attr("a1", "e1", 2),
            _attr("a2", "e2", 3),
            _attr("a3", "e3", None),
        ]
        fe, fa = filter_pending(entities, attrs, chapter=2)
        assert [a.attribute_id for a in fa] == ["a1"]
        # e1 被 a1 引用入选；e2/e3 未被引用落选
        assert [e.entity_id for e in fe] == ["e1"]

    def test_no_filter_keeps_everything(self) -> None:
        entities = [_entity("e1"), _entity("e2")]
        attrs = [_attr("a1", "e1", 2), _attr("a2", "e2", 3)]
        fe, fa = filter_pending(entities, attrs)
        assert len(fe) == 2
        assert len(fa) == 2

    def test_chapter_no_match_is_empty(self) -> None:
        entities = [_entity("e1")]
        attrs = [_attr("a1", "e1", 2)]
        fe, fa = filter_pending(entities, attrs, chapter=9)
        assert fe == [] and fa == []


class TestSourceFilter:
    def test_source_only_attributes(self) -> None:
        entities = [_entity("e1"), _entity("e2")]
        attrs = [
            _attr("a1", "e1", 2, source="extract"),
            _attr("a2", "e2", 2, source="human"),
        ]
        fe, fa = filter_pending(entities, attrs, source="extract")
        assert [a.attribute_id for a in fa] == ["a1"]
        assert [e.entity_id for e in fe] == ["e1"]


class TestKindFilter:
    def test_kind_entity_only(self) -> None:
        entities = [_entity("e1"), _entity("e2")]
        attrs = [_attr("a1", "e1", 2)]
        fe, fa = filter_pending(entities, attrs, kind="entity")
        assert len(fe) == 2 and fa == []

    def test_kind_attribute_only(self) -> None:
        entities = [_entity("e1"), _entity("e2")]
        attrs = [_attr("a1", "e1", 2)]
        fe, fa = filter_pending(entities, attrs, kind="attribute")
        assert fe == [] and [a.attribute_id for a in fa] == ["a1"]

    def test_combined_chapter_and_source(self) -> None:
        entities = [_entity("e1"), _entity("e2")]
        attrs = [
            _attr("a1", "e1", 2, source="extract"),
            _attr("a2", "e2", 2, source="human"),
            _attr("a3", "e1", 3, source="extract"),
        ]
        fe, fa = filter_pending(entities, attrs, chapter=2, source="extract")
        assert [a.attribute_id for a in fa] == ["a1"]
        assert [e.entity_id for e in fe] == ["e1"]

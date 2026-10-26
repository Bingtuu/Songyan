"""Thin-wrapper runtime: approved plan cards are the chapter bible.

Writing and revision read those cards. Body extracts stay out of canon.
Plan-fact failures are shown to the human gate and do not change its routing.
SettlementExtractor is not a plan-canon writer.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from songyan.agents.revision_handler import _render_prompt as render_revision_prompt
from songyan.agents.revision_handler._segmented_revision import _render_scene_prompt
from songyan.agents.writer import _render_prompt
from songyan.db.connection import get_db
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import ProjectRepository
from songyan.models.chapter import ChapterGoal, ChapterVersion
from songyan.models.context import ContextPackage
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClaim,
    PlanClue,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)
from songyan.models.project import ProjectSetting
from songyan.plan_checks.bible import (
    load_chapter_plan_bible,
    plan_fact_gate_failure_lines,
    wrap_writing_prompt,
)
from songyan.workflows._nodes import (
    context_manager_node,
    human_gate_node,
    revision_handler_node,
    rule_auditor_node,
)

_TABLES = (
    "plan_entities",
    "plan_attributes",
    "plan_events",
    "plan_time_anchors",
    "plan_clues",
)


async def _gate_db(tmp_path: Path, monkeypatch) -> None:
    import songyan.db.connection as conn_mod
    from songyan.db.migrations import init_schema

    db_path = tmp_path / "bible.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)


async def _counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    async with get_db() as conn:
        for table in _TABLES:
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            assert row is not None
            counts[table] = int(row[0])
    return counts


async def _seed_chapter_two() -> None:
    """Approved chapter-2 cards, plus rows the bible must not treat as canon."""
    projects = ProjectRepository()
    setting = ProjectSetting(genre_id="scifi", mode_id="webnovel", protagonist_name="陈照")
    await projects.create(setting, "p1")
    await projects.create(setting, "other-book")
    repo = PlanFactRepository()
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-knife",
            project_id="p1",
            entity_type="object",
            aliases=["银刀", "那把刀"],
            approval_status="approved",
        )
    )
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-other",
            project_id="p1",
            entity_type="object",
            aliases=["另一件"],
            approval_status="approved",
        )
    )
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-pending",
            project_id="p1",
            entity_type="object",
            aliases=["待审刀"],
            approval_status="pending",
        )
    )
    await repo.write_time_anchor(
        PlanTimeAnchor(
            anchor_id="ta-march",
            project_id="p1",
            date="1931-03",
            kind="story",
            approval_status="approved",
        )
    )
    await repo.write_time_anchor(
        PlanTimeAnchor(
            anchor_id="ta-unused",
            project_id="p1",
            date="1931-11后",
            kind="history",
            approval_status="approved",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-direction",
            project_id="p1",
            entity_id="ent-knife",
            key="direction",
            value="东",
            valid_from_ch=1,
            valid_to_ch=3,
            source="plan",
            approval_status="approved",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-pending",
            project_id="p1",
            entity_id="ent-knife",
            key="direction",
            value="南",
            valid_from_ch=1,
            valid_to_ch=3,
            source="human",
            approval_status="pending",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-later",
            project_id="p1",
            entity_id="ent-knife",
            key="direction",
            value="以后才朝北",
            valid_from_ch=9,
            valid_to_ch=9,
            source="plan",
            approval_status="approved",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-unreferenced",
            project_id="p1",
            entity_id="ent-other",
            key="color",
            value="不相关的颜色",
            source="plan",
            approval_status="approved",
        )
    )
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-other-book",
            project_id="other-book",
            entity_type="object",
            aliases=["别书的刀"],
            approval_status="approved",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-elsewhere",
            project_id="other-book",
            entity_id="ent-other-book",
            key="direction",
            value="别的书",
            source="plan",
            approval_status="approved",
        )
    )
    await repo.write_event(
        PlanEvent(
            event_id="evt-other",
            project_id="other-book",
            ch=2,
            participants=["ent-other-book"],
            claims=[PlanClaim(claim_id="claim-other", text="别的书的主张")],
            approval_status="approved",
        )
    )
    await repo.write_event(
        PlanEvent(
            event_id="evt-ch2",
            project_id="p1",
            ch=2,
            time_anchor_id="ta-march",
            participants=["ent-knife"],
            claims=[PlanClaim(claim_id="claim-dir", text="刀口朝东")],
            approval_status="approved",
        )
    )
    await repo.write_event(
        PlanEvent(
            event_id="evt-ch3",
            project_id="p1",
            ch=3,
            participants=["ent-knife"],
            claims=[PlanClaim(claim_id="claim-ch3", text="只属于第三章")],
            approval_status="approved",
        )
    )
    await repo.write_event(
        PlanEvent(
            event_id="evt-pending",
            project_id="p1",
            ch=2,
            participants=["ent-pending"],
            claims=[PlanClaim(claim_id="claim-pending", text="待审主张")],
            approval_status="pending",
        )
    )
    await repo.write_clue(
        PlanClue(
            clue_id="clue-blunt",
            project_id="p1",
            planted_ch=1,
            must_mention_in=[1, 2],
            label="钝器伤",
            mention_terms=["钝器伤"],
            approval_status="approved",
        )
    )
    await repo.write_clue(
        PlanClue(
            clue_id="clue-pending",
            project_id="p1",
            planted_ch=2,
            must_mention_in=[2],
            label="不该出现",
            mention_terms=["不该出现"],
            approval_status="pending",
        )
    )


def _failed_report() -> dict[str, object]:
    return {
        "project_id": "p1",
        "chapter": 2,
        "passed": False,
        "missing_mentions": [
            {
                "point_id": "clue-blunt",
                "label": "钝器伤",
                "chapter": 2,
                "missing_terms": ["钝器伤"],
            }
        ],
        "claim_verdicts": [
            {
                "claim_id": "claim-dir",
                "text": "刀口朝东",
                "status": "contradicted",
                "citation": "朝西",
            },
            {
                "claim_id": "claim-ok",
                "text": "人还在",
                "status": "supported",
                "citation": "人",
            },
            {
                "claim_id": "claim-miss",
                "text": "后脑有伤",
                "status": "unmentioned",
                "citation": "",
            },
        ],
        "attribute_mismatches": [
            {
                "attribute_id": "attr-direction",
                "entity_id": "ent-knife",
                "key": "direction",
                "approved_value": "东",
                "extract_value": "西",
                "chapter": 2,
            }
        ],
    }


async def test_bible_reads_approved_cards_for_this_chapter_only(
    tmp_path: Path, monkeypatch
) -> None:
    await _gate_db(tmp_path, monkeypatch)
    await _seed_chapter_two()

    bible = await load_chapter_plan_bible("p1", 2)

    assert bible.entity_ids == ["ent-knife"]
    assert bible.attribute_ids == ["attr-direction"]
    assert bible.event_ids == ["evt-ch2"]
    assert bible.clue_ids == ["clue-blunt"]
    assert bible.time_anchor_ids == ["ta-march"]
    assert "银刀" in bible.text
    assert "ent-knife.direction = 东" in bible.text
    assert "来源 plan" in bible.text
    assert "刀口朝东" in bible.text
    assert "1931-03" in bible.text
    assert "钝器伤" in bible.text
    banned = (
        "南",
        "以后才朝北",
        "不相关的颜色",
        "别的书",
        "只属于第三章",
        "待审主张",
        "待审刀",
        "不该出现",
        "1931-11后",
    )
    for phrase in banned:
        assert phrase not in bible.text


async def test_chapter_without_approved_cards_has_an_empty_bible(
    tmp_path: Path, monkeypatch
) -> None:
    await _gate_db(tmp_path, monkeypatch)
    await _seed_chapter_two()

    bible = await load_chapter_plan_bible("p1", 4)

    assert bible.text == ""
    assert bible.event_ids == []
    assert bible.clue_ids == []
    assert bible.attribute_ids == []


async def test_missing_database_does_not_create_a_file(tmp_path: Path, monkeypatch) -> None:
    import songyan.db.connection as conn_mod

    missing = tmp_path / "absent.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{missing}"})(),
    )

    bible = await load_chapter_plan_bible("p1", 1)

    assert bible.text == ""
    assert not missing.exists()


async def test_context_snapshot_carries_the_bible_into_the_writer_prompt(
    tmp_path: Path, monkeypatch
) -> None:
    await _gate_db(tmp_path, monkeypatch)
    await _seed_chapter_two()
    goal = ChapterGoal(chapter_number=2, word_count_target=3000)
    snapshot_repo = AsyncMock()
    snapshot_repo.create = AsyncMock()

    with (
        patch(
            "songyan.workflows._nodes.load_chapter_goal",
            new_callable=AsyncMock,
            return_value=goal,
        ),
        patch(
            "songyan.workflows._nodes.load_creative_brief",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "songyan.workflows._nodes.assemble_context_package",
            new_callable=AsyncMock,
            return_value=ContextPackage(chapter_goal=goal),
        ),
        patch(
            "songyan.workflows._nodes.ContextSnapshotRepository",
            return_value=snapshot_repo,
        ),
    ):
        result = await context_manager_node(
            {
                "project_id": "p1",
                "chapter_number": 2,
                "chapter_goal_id": "goal-1",
                "human_instructions": [{"action": "revise", "content": "保留黑匣子"}],
            }
        )

    assert result["status"] == "writing"
    snapshot = snapshot_repo.create.await_args.args[0]
    assert snapshot.payload["human_instructions"][0]["content"] == "保留黑匣子"
    restored = ContextPackage.model_validate(snapshot.payload)
    prompt = _render_prompt(restored)
    assert "本章事实圣经（已批准计划卡）" in prompt
    assert "不是已成立事实" in prompt
    assert "刀口朝东" in prompt
    assert "南" not in restored.plan_bible
    assert prompt.index("本章事实圣经") < prompt.index("章节目标")


async def test_writer_prompt_without_a_bible_does_not_invent_one() -> None:
    goal = ChapterGoal(chapter_number=2, word_count_target=3000)
    prompt = _render_prompt(ContextPackage(chapter_goal=goal))
    assert "本章事实圣经" not in prompt
    assert wrap_writing_prompt(prompt, "  ") == prompt


async def test_revision_prompts_open_with_the_same_bible() -> None:
    card = "ent-knife.direction = 东"
    revision = render_revision_prompt("原文段落。", [], [], plan_bible=card)
    scene = _render_scene_prompt("场景段落。", [], [], plan_bible=card)
    assert revision.index("本章事实圣经（已批准计划卡）") < revision.index("原文段落")
    assert scene.index("本章事实圣经（已批准计划卡）") < scene.index("场景段落")
    for prompt in (revision, scene):
        assert card in prompt
        assert "不是已成立事实" in prompt


async def test_revision_node_passes_the_loaded_bible() -> None:
    version = ChapterVersion(
        version_id="v-1",
        project_id="p1",
        chapter_number=2,
        content="刀口朝西。",
        word_count=5,
    )
    output = SimpleNamespace(content_preservation_ratio=0.1)
    with (
        patch(
            "songyan.workflows._nodes.load_version",
            new_callable=AsyncMock,
            return_value=version,
        ),
        patch(
            "songyan.workflows._nodes.load_merged_report",
            new_callable=AsyncMock,
            return_value=SimpleNamespace(),
        ),
        patch("songyan.workflows._nodes.ReviewReportRepository") as repo_cls,
        patch(
            "songyan.workflows._nodes.load_chapter_goal",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "songyan.workflows._nodes.load_project",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "songyan.workflows._nodes.load_chapter_plan_bible",
            new_callable=AsyncMock,
            return_value=SimpleNamespace(text="刀口朝东"),
        ) as load_bible,
        patch(
            "songyan.workflows._nodes.run_revision",
            new_callable=AsyncMock,
            return_value=(output, "短"),
        ) as run_revision,
    ):
        repo_cls.return_value.get_by_version = AsyncMock(return_value=None)
        result = await revision_handler_node(
            {
                "current_version_id": "v-1",
                "project_id": "p1",
                "chapter_number": 2,
                "chapter_goal_id": "",
                "revision_round": 0,
            }
        )

    load_bible.assert_awaited_once_with("p1", 2)
    assert run_revision.await_args.kwargs["plan_bible"] == "刀口朝东"
    assert result["status"] == "rule_auditing"
    assert result["current_version_id"] == "v-1"


async def test_review_does_not_promote_body_extracts_into_canon(
    tmp_path: Path, monkeypatch
) -> None:
    await _gate_db(tmp_path, monkeypatch)
    await _seed_chapter_two()
    before = await _counts()
    version = ChapterVersion(
        version_id="v-drift",
        project_id="p1",
        chapter_number=2,
        content="刀口朝西，没有钝器伤。",
        word_count=12,
    )
    state = {
        "project_id": "p1",
        "chapter_number": 2,
        "current_version_id": "v-drift",
        "chapter_goal_id": "",
        "context_package": SimpleNamespace(mandatory_references=None),
        "_plan_attribute_extracts": [
            {"entity_id": "ent-knife", "key": "direction", "value": "西", "chapter": 2}
        ],
        "_plan_claim_anchors": [
            {"claim_id": "claim-dir", "contradict_terms": ["朝西"]},
        ],
    }
    with (
        patch(
            "songyan.workflows._nodes.load_version",
            new_callable=AsyncMock,
            return_value=version,
        ),
        patch("songyan.workflows._nodes.save_rule_audit", new_callable=AsyncMock),
    ):
        result = await rule_auditor_node(state)

    repo = PlanFactRepository()
    canon = await repo.list_canon_attributes("p1")
    pending = await repo.list_pending_attributes("p1")
    assert [row.value for row in canon if row.entity_id == "ent-knife"] == ["东", "以后才朝北"]
    assert [row.value for row in pending] == ["南"]
    assert await _counts() == before
    assert result["status"] == "llm_auditing"
    assert result["_plan_fact_gate"]["passed"] is False
    assert "西" not in {row.value for row in canon}
    assert "西" not in {row.value for row in pending}


async def test_human_gate_shows_failures_without_changing_accept_routing() -> None:
    version = ChapterVersion(
        version_id="v-1",
        project_id="p1",
        chapter_number=2,
        content="刀口朝西。",
        word_count=5,
    )
    with (
        patch(
            "songyan.workflows._nodes.load_version",
            new_callable=AsyncMock,
            return_value=version,
        ),
        patch("songyan.workflows._nodes.interrupt", return_value="accept") as interrupt,
    ):
        result = await human_gate_node(
            {
                "current_version_id": "v-1",
                "project_id": "p1",
                "chapter_number": 2,
                "_plan_fact_gate": _failed_report(),
            }
        )

    payload = interrupt.call_args.args[0]
    lines = payload["plan_fact_gate_failures"]
    assert payload["options"] == ["accept", "edit", "reject", "back"]
    assert any("clue-blunt" in line and "钝器伤" in line for line in lines)
    assert any("claim-dir" in line and "刀口朝东" in line for line in lines)
    assert any("claim-miss" in line and "后脑有伤" in line for line in lines)
    assert any("圣经" in line and "东" in line and "西" in line for line in lines)
    assert not any("人还在" in line for line in lines)
    assert result["status"] == "settlement"
    assert result["human_decision"] == "accept"


async def test_human_gate_omits_failures_when_the_gate_passed_or_is_absent() -> None:
    version = ChapterVersion(
        version_id="v-1",
        project_id="p1",
        chapter_number=1,
        content="正文。",
        word_count=3,
    )
    passed = _failed_report()
    passed["passed"] = True
    with (
        patch(
            "songyan.workflows._nodes.load_version",
            new_callable=AsyncMock,
            return_value=version,
        ),
        patch("songyan.workflows._nodes.interrupt", return_value="reject") as interrupt,
    ):
        await human_gate_node(
            {
                "current_version_id": "v-1",
                "project_id": "p1",
                "chapter_number": 1,
                "_plan_fact_gate": passed,
            }
        )
        await human_gate_node(
            {"current_version_id": "v-1", "project_id": "p1", "chapter_number": 1}
        )

    first, second = (call.args[0] for call in interrupt.call_args_list)
    assert first["plan_fact_gate_failures"] == []
    assert second["plan_fact_gate_failures"] == []
    assert plan_fact_gate_failure_lines(None) == []
    assert plan_fact_gate_failure_lines("nope") == []


def test_settlement_extractor_does_not_reference_plan_canon() -> None:
    root = Path("src/songyan/agents/settlement_extractor")
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        joined = " ".join(imported)
        assert "plan_fact" not in joined
        assert "plan_checks" not in joined
        assert "plan_entities" not in joined

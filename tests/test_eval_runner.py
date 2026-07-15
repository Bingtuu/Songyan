"""Eval runner tests — 种子项目导入 + 评测 runner 集成."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from evals.metrics import MetricsCollector
from evals.models import SeedProjectConfig
from evals.runner import import_seed_chapter, import_seed_project, run_seed_project
from songyan.db.connection import get_db
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.models import (
    ChapterVersion,
    CharacterUpdate,
    LiteraryAuditResult,
    LiteraryObservation,
    MergedReviewReport,
    RuleAuditResult,
    StateSettlement,
)
from songyan.workflows.phase1_graph import (
    reset_checkpointer,
    resume_human_confirm,
    run_chapter_pipeline,
)

# ---------------------------------------------------------------------------
# Mock LLM fixture (duplicated from tests/integration/conftest.py for isolation)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_call_llm():
    """Fixture that patches all Agent call_llm imports with a sequenced mock."""
    async def _mock(
        prompt: str = "",
        *,
        temperature: float = 0.7,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> str:
        responses = _mock.responses  # type: ignore[attr-defined]
        count = _mock._call_count  # type: ignore[attr-defined]
        if count >= len(responses):
            raise RuntimeError(
                f"mock_call_llm ran out of responses (call {count}, "
                f"only {len(responses)} configured). Prompt snippet: {prompt[:80]}"
            )
        resp = responses[count]
        _mock._call_count = count + 1  # type: ignore[attr-defined]
        return resp

    _mock.responses: list[str] = []  # type: ignore[attr-defined]
    _mock._call_count: int = 0  # type: ignore[attr-defined]

    targets = [
        "songyan.agents.goal_planner.call_llm",
        "songyan.agents.creative_director.call_llm",
        "songyan.agents.writer.call_llm",
        "songyan.agents.llm_auditor.call_llm",
        "songyan.agents.literary_auditor.call_llm",
        "songyan.agents.revision_handler.call_llm",
        "songyan.agents.settlement_extractor.call_llm",
        "songyan.agents.summary_writer.call_llm",
    ]

    with contextlib.ExitStack() as stack:
        for target in targets:
            stack.enter_context(patch(target, _mock))
        yield _mock


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------


def _goal_resp() -> str:
    return json.dumps(
        {
            "target_events": ["测试事件A", "测试事件B"],
            "emotional_arc": "紧张→兴奋",
            "hooks": {"opening": "悬念开场", "closing": "悬念收尾"},
            "obligations": ["保持主角性格"],
            "word_count_target": 100,
            "chapter_type": "opening",
        }
    )


def _brief_resp() -> str:
    return json.dumps(
        {
            "creative_intent": "展现主角果敢",
            "required_tensions": [
                {"tension_type": "value_conflict", "description": "被追杀", "intensity": 8}
            ],
            "forbidden_patterns": ["旁白解释内心"],
            "allowed_fissures": [],
            "style_constraints": ["快节奏"],
            "reader_contract": "每800字一个爽点",
        }
    )


def _writer_resp() -> str:
    filler = (
        "主角稳住呼吸，沿着石壁缓慢前进，灵气在经脉中一寸寸回流。"
        "他没有急着冲动出手，而是观察符文的明暗变化，确认追兵的脚步正在远去。"
    ) * 16
    second_filler = (
        "主角把掌心贴在青铜门缝旁，感受灵压像潮水一样沿着指节回旋。"
        "他放慢吐息，记下每一道暗纹亮起的次序，等最后的光点沉入石缝。"
    ) * 16
    return (
        "### Scene 1\n\n"
        "测试正文内容。\n\n"
        "「小子，交出玉佩！」领头大汉狞笑道。\n\n"
        "主角冷笑一声，纵身跃下悬崖。\n\n"
        "下落途中，他抓住藤蔓，荡进石缝。\n\n"
        f"{filler}\n\n"
        "### Scene 2\n\n"
        "石缝尽头，一扇青铜大门静静矗立。\n\n"
        "「这是……古修洞府？」主角瞳孔一缩。\n\n"
        "大门缓缓开启，灵气扑面而来。\n\n"
        "门后，是一条通往未知的甬道。\n"
        f"{second_filler}\n"
        "甬道尽头忽然传来没有人声的低语：下一步，才是真正的考验？\n"
    )


def _llm_clean_resp() -> str:
    return json.dumps(
        {
            "issues": [],
            "dimension_scores": {k: 8.0 for k in [
                "world_consistency", "character_behavior", "timeline",
                "new_setting_unregistered", "narrative_pacing", "narrative_hook",
                "info_dump", "dialogue_distinctness", "dialogue_subtext",
                "description_sensory", "show_dont_tell", "genre_numerical",
            ]},
            "cliche_risk_score": 3.0,
            "character_autonomy_score": 7.0,
            "conceptual_idling_score": 2.0,
            "summary": "整体良好",
        }
    )


def _literary_resp() -> str:
    return json.dumps(
        {
            "observations": [
                {
                    "observation_type": "excessive_smoothing",
                    "description": "转折略显突兀",
                    "severity": "minor",
                    "affected_text": "纵身跃下悬崖",
                    "recommendation": "可铺垫犹豫瞬间",
                }
            ],
            "overall_quality_score": 6.5,
            "protected_elements": [],
        }
    )


def _settlement_resp() -> str:
    return json.dumps(
        {
            "character_updates": [],  # 空列表避免不存在的 character_id 导致 FK 失败
            "new_settings": [
                {
                    "setting_name": "青铜大门",
                    "description": "刻满符文的古老门户",
                    "source_quote": "一扇青铜大门静静矗立",
                    "setting_key": "xuanhuan.artifact.bronze_gate",
                }
            ],
            "foreshadowing_updates": [],
            "numerical_updates": [],
            "validation_status": "valid",
            "validation_errors": [],
        }
    )


def _summary_resp() -> str:
    return json.dumps(
        {"plot_summary": "主角被逼悬崖，发现洞府", "emotional_tone": "紧张兴奋"}
    )


# ---------------------------------------------------------------------------
# Layer 1: Import tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_seed_project_success(test_db) -> None:
    """import_seed_project 成功返回 project_id，DB 数据正确."""
    config_path = Path("evals/seeds/xuanhuan_webnovel.json")
    project_id = await import_seed_project(str(config_path))

    assert project_id.startswith("proj-")

    config = SeedProjectConfig.model_validate_json(config_path.read_text(encoding="utf-8"))
    project = await ProjectRepository().get(project_id)
    assert project is not None
    assert project.title == config.project_name
    assert project.genre_id == config.genre_id

    chars = await CharacterRepository().list_by_project(project_id)
    assert len(chars) == len(config.characters)

    # 验证 setting_snapshots
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM setting_snapshots WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] == len(config.initial_settings)


@pytest.mark.asyncio
async def test_import_seed_project_invalid_json(test_db) -> None:
    """无效 JSON / 缺失必填字段 → 抛出明确异常."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write('{"project_name": "test"}')  # 缺失 genre_id 等必填字段
        invalid_path = f.name

    from pydantic import ValidationError

    with pytest.raises((ValidationError, json.JSONDecodeError)):
        await import_seed_project(invalid_path)


# ---------------------------------------------------------------------------
# Layer 2: Seed chapter import tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_seed_chapter_success(test_db) -> None:
    """import_seed_chapter 成功，chapter_heads 指向 accepted 版本."""
    # 先导入项目
    config_path = Path("evals/seeds/xuanhuan_webnovel.json")
    project_id = await import_seed_project(str(config_path))

    # 导入种子章节
    chapter_path = Path("evals/seeds/chapters/xuanhuan_ch1.md")
    version_id = await import_seed_chapter(project_id, str(chapter_path), chapter_number=1)

    assert version_id.startswith("v-")

    version = await ChapterVersionRepository().get(version_id)
    assert version is not None
    assert version.version_type == "accepted"
    assert version.word_count > 0

    head = await ChapterHeadRepository().get(project_id, 1)
    assert head is not None
    assert head.accepted_version_id == version_id
    assert head.status == "accepted"

    # 验证 summary 已写入
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM summaries WHERE project_id = ? AND chapter_number = ?",
            (project_id, 1),
        )
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 1


# ---------------------------------------------------------------------------
# Layer 3: Runner integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.performance
async def test_run_seed_project_mock_success(test_db, mock_call_llm) -> None:
    """run_seed_project 在 mock LLM 下完整跑通，返回 success."""
    await reset_checkpointer()

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        _goal_resp(),
        _brief_resp(),
        _writer_resp(),
        _llm_clean_resp(),
        _literary_resp(),
        _settlement_resp(),
        _summary_resp(),
    ]

    config_path = Path("evals/seeds/xuanhuan_webnovel.json")
    chapter_path = Path("evals/seeds/chapters/xuanhuan_ch1.md")
    output_dir = Path("evals/output/test_run_01")

    result = await run_seed_project(
        project_config_path=str(config_path),
        seed_chapter_path=str(chapter_path),
        output_dir=str(output_dir),
        auto_accept=True,
    )

    assert result.success is True
    assert result.project_id.startswith("proj-")
    assert result.chapter_version_id != ""
    assert result.settlement_id != ""
    assert result.summary_id != ""
    assert result.duration_ms > 0

    # 输出目录应包含 5 个文件
    assert (output_dir / "result.json").exists()
    assert (output_dir / "chapter_v2.md").exists()
    assert (output_dir / "review_report.json").exists()
    assert (output_dir / "settlement.json").exists()
    assert (output_dir / "summary.json").exists()


@pytest.mark.asyncio
@pytest.mark.performance
async def test_run_seed_project_repeatable(test_db, mock_call_llm) -> None:
    """同一配置重复执行产生不同 project_id，不冲突."""
    await reset_checkpointer()

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        _goal_resp(),
        _brief_resp(),
        _writer_resp(),
        _llm_clean_resp(),
        _literary_resp(),
        _settlement_resp(),
        _summary_resp(),
    ]

    config_path = Path("evals/seeds/xuanhuan_webnovel.json")
    chapter_path = Path("evals/seeds/chapters/xuanhuan_ch1.md")

    result1 = await run_seed_project(
        project_config_path=str(config_path),
        seed_chapter_path=str(chapter_path),
        output_dir="evals/output/test_repeat_01",
        auto_accept=True,
    )

    # 重置 mock responses（因为 mock_call_llm 是每个测试独立的 fixture，
    # 但 run_seed_project 内部会消耗 responses，第二次需要重新设置）
    mock_call_llm.responses = [  # type: ignore[attr-defined]
        _goal_resp(),
        _brief_resp(),
        _writer_resp(),
        _llm_clean_resp(),
        _literary_resp(),
        _settlement_resp(),
        _summary_resp(),
    ]
    mock_call_llm._call_count = 0  # type: ignore[attr-defined]
    await reset_checkpointer()

    result2 = await run_seed_project(
        project_config_path=str(config_path),
        seed_chapter_path=str(chapter_path),
        output_dir="evals/output/test_repeat_02",
        auto_accept=True,
    )

    assert result1.project_id != result2.project_id
    assert result1.success is True
    assert result2.success is True


@pytest.mark.performance
@pytest.mark.asyncio
async def test_run_seed_project_all_configs(test_db, mock_call_llm) -> None:
    """3 个种子配置均可成功导入并跑通."""
    configs = [
        ("evals/seeds/xuanhuan_webnovel.json", "evals/seeds/chapters/xuanhuan_ch1.md"),
        ("evals/seeds/urban_hybrid.json", "evals/seeds/chapters/urban_ch1.md"),
        ("evals/seeds/scifi_webnovel.json", "evals/seeds/chapters/scifi_ch1.md"),
    ]

    for idx, (cfg_path, ch_path) in enumerate(configs):
        await reset_checkpointer()
        mock_call_llm.responses = [  # type: ignore[attr-defined]
            _goal_resp(),
            _brief_resp(),
            _writer_resp(),
            _llm_clean_resp(),
            _literary_resp(),
            _settlement_resp(),
            _summary_resp(),
        ]
        mock_call_llm._call_count = 0  # type: ignore[attr-defined]

        result = await run_seed_project(
            project_config_path=cfg_path,
            seed_chapter_path=ch_path,
            output_dir=f"evals/output/test_all_{idx}",
            auto_accept=True,
        )
        assert result.success is True, f"Config {cfg_path} failed"

        # 验证核心输出文件存在
        output_dir = Path(f"evals/output/test_all_{idx}")
        assert (output_dir / "result.json").exists()
        assert (output_dir / "chapter_v2.md").exists()
        assert (output_dir / "review_report.json").exists()


# ---------------------------------------------------------------------------
# Metrics unit tests
# ---------------------------------------------------------------------------


def test_hard_errors_calculation() -> None:
    """hard_errors 正确统计 world_consistency critical issues."""
    _issue = lambda iid, cat, sev: {  # noqa: E731
        "issue_id": iid,
        "category": cat,
        "severity": sev,
        "evidence_quote": "q",
        "evidence_location": "l",
        "issue_description": "d",
        "expected": "e",
        "actual": "a",
        "suggested_fix": "f",
        "fix_type": "patch",
        "confidence": 0.9,
    }
    report = MergedReviewReport(
        chapter_version_id="v-1",
        issues=[
            _issue("i1", "world_consistency", "critical"),
            _issue("i2", "timeline", "critical"),
            _issue("i3", "world_consistency", "major"),
        ],
    )
    mc = MetricsCollector(
        version=ChapterVersion(version_id="v-1", project_id="p-1", chapter_number=2),
        review_report=report,
        settlement=StateSettlement(),
    )
    metrics = mc.collect()
    assert metrics["hard_errors"] == 1


def test_ai_tell_count_extraction() -> None:
    report = MergedReviewReport(
        chapter_version_id="v-1",
        rule_audit=RuleAuditResult(ai_tell_count=3),
        ai_tell_count=3,
    )
    mc = MetricsCollector(
        version=ChapterVersion(version_id="v-1", project_id="p-1", chapter_number=2),
        review_report=report,
        settlement=StateSettlement(),
    )
    assert mc.collect()["ai_tell_count"] == 3


def test_fatigue_word_count_extraction() -> None:
    report = MergedReviewReport(
        chapter_version_id="v-1",
        rule_audit=RuleAuditResult(fatigue_word_count=5),
        fatigue_word_count=5,
    )
    mc = MetricsCollector(
        version=ChapterVersion(version_id="v-1", project_id="p-1", chapter_number=2),
        review_report=report,
        settlement=StateSettlement(),
    )
    assert mc.collect()["fatigue_word_count"] == 5


def test_hook_opening_closing_merge() -> None:
    """Rule has hook = pass; Rule missing but LLM narrative_hook >= 7 = pass."""
    report_with_hook = MergedReviewReport(
        chapter_version_id="v-1",
        has_opening_hook=True,
        has_ending_hook=False,
    )
    mc1 = MetricsCollector(
        version=ChapterVersion(version_id="v-1", project_id="p-1", chapter_number=2),
        review_report=report_with_hook,
        settlement=StateSettlement(),
    )
    assert mc1.collect()["hook_opening_pass"] == 1
    assert mc1.collect()["hook_closing_pass"] == 0

    report_llm_hook = MergedReviewReport(
        chapter_version_id="v-1",
        has_opening_hook=False,
        has_ending_hook=False,
        llm_audit={
            "auditor_id": "llm",
            "issues": [],
            "dimension_scores": {"narrative_hook": 8.0},
            "cliche_risk_score": 0,
            "character_autonomy_score": 0,
            "conceptual_idling_score": 0,
            "summary": "",
            "duration_ms": 0,
        }
    )
    mc2 = MetricsCollector(
        version=ChapterVersion(version_id="v-1", project_id="p-1", chapter_number=2),
        review_report=report_llm_hook,
        settlement=StateSettlement(),
    )
    assert mc2.collect()["hook_opening_pass"] == 1


def test_conceptual_idling_count() -> None:
    literary = LiteraryAuditResult(
        observations=[
            LiteraryObservation(
                observation_id="o1", observation_type="conceptual_idling", description="d1"
            ),
            LiteraryObservation(
                observation_id="o2", observation_type="excessive_smoothing", description="d2"
            ),
            LiteraryObservation(
                observation_id="o3", observation_type="conceptual_idling", description="d3"
            ),
        ]
    )
    mc = MetricsCollector(
        version=ChapterVersion(version_id="v-1", project_id="p-1", chapter_number=2),
        review_report=MergedReviewReport(chapter_version_id="v-1"),
        settlement=StateSettlement(),
        literary_result=literary,
    )
    assert mc.collect()["conceptual_idling_count"] == 2


def test_revision_new_issues() -> None:
    _issue = lambda iid, cat, sev: {  # noqa: E731
        "issue_id": iid,
        "category": cat,
        "severity": sev,
        "evidence_quote": "q",
        "evidence_location": "l",
        "issue_description": "d",
        "expected": "e",
        "actual": "a",
        "suggested_fix": "f",
        "fix_type": "patch",
        "confidence": 0.9,
    }
    prev = MergedReviewReport(
        chapter_version_id="v-1",
        issues=[_issue("i1", "world_consistency", "critical")],
    )
    curr = MergedReviewReport(
        chapter_version_id="v-2",
        issues=[
            _issue("i1", "world_consistency", "critical"),
            _issue("i2", "timeline", "major"),
        ],
    )
    mc = MetricsCollector(
        version=ChapterVersion(version_id="v-2", project_id="p-1", chapter_number=2),
        review_report=curr,
        settlement=StateSettlement(),
        previous_report=prev,
    )
    assert mc.collect()["revision_new_issues"] == 1

    # 无 previous_report 时返回 None
    mc2 = MetricsCollector(
        version=ChapterVersion(version_id="v-2", project_id="p-1", chapter_number=2),
        review_report=curr,
        settlement=StateSettlement(),
    )
    assert mc2.collect()["revision_new_issues"] is None


@pytest.mark.asyncio
async def test_is_pass(test_db) -> None:
    """is_pass() 在达标/不达标场景下返回正确."""
    # 达标场景：空 settlement（无 DB IO），clean report
    clean_report = MergedReviewReport(
        chapter_version_id="v-1",
        has_opening_hook=True,
        has_ending_hook=True,
        issues=[],
    )
    mc_pass = MetricsCollector(
        version=ChapterVersion(version_id="v-1", project_id="p-1", chapter_number=2),
        review_report=clean_report,
        settlement=StateSettlement(),
    )
    assert await mc_pass.is_pass() is True

    # 不达标场景：有 critical world_consistency issue
    bad_report = MergedReviewReport(
        chapter_version_id="v-1",
        has_opening_hook=True,
        has_ending_hook=True,
        issues=[
            {
                "issue_id": "i1",
                "category": "world_consistency",
                "severity": "critical",
                "evidence_quote": "q",
                "evidence_location": "l",
                "issue_description": "d",
                "expected": "e",
                "actual": "a",
                "suggested_fix": "f",
                "fix_type": "patch",
                "confidence": 0.9,
            }
        ],
    )
    mc_fail = MetricsCollector(
        version=ChapterVersion(version_id="v-1", project_id="p-1", chapter_number=2),
        review_report=bad_report,
        settlement=StateSettlement(),
    )
    assert await mc_fail.is_pass() is False


@pytest.mark.asyncio
async def test_settlement_field_accuracy_with_updates(test_db) -> None:
    """settlement_field_accuracy 在有实际 character_updates 时正确计算."""
    project_id = "p-test-sfa"

    # 1. 先创建一个角色和一个 seed version
    async with get_db() as conn:
        await conn.execute(
            "INSERT INTO projects (project_id, title, genre_id, protagonist_name) "
            "VALUES (?, ?, ?, ?)",
            (project_id, "test", "xuanhuan", "主角"),
        )
        await conn.execute(
            "INSERT INTO characters (character_id, project_id, name, role_type) "
            "VALUES (?, ?, ?, ?)",
            ("char-test", project_id, "主角", "protagonist"),
        )
        await conn.execute(
            "INSERT INTO chapter_versions "
            "(version_id, project_id, chapter_number, version_number, version_type, content) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("v-seed", project_id, 1, 1, "accepted", "seed"),
        )
        # 写入 seed character state
        await conn.execute(
            "INSERT INTO character_states (character_id, field, value, source_version_id) "
            "VALUES (?, ?, ?, ?)",
            ("char-test", "level", "1", "v-seed"),
        )
        await conn.commit()

    # 2. settlement 声称从 level=1 更新到 level=2
    settlement = StateSettlement(
        character_updates=[
            CharacterUpdate(
                character_id="char-test",
                field="level",
                old_value="1",
                new_value="2",
                source_quote="",
            )
        ]
    )

    # 3. 模拟 settlement 已应用：先创建 v-new 版本，再写入 new_value=2
    async with get_db() as conn:
        await conn.execute(
            "INSERT INTO chapter_versions "
            "(version_id, project_id, chapter_number, version_number, version_type, content) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("v-new", project_id, 2, 1, "accepted", "chapter content"),
        )
        await conn.execute(
            "INSERT INTO character_states (character_id, field, value, source_version_id) "
            "VALUES (?, ?, ?, ?)",
            ("char-test", "level", "2", "v-new"),
        )
        await conn.commit()

    mc = MetricsCollector(
        version=ChapterVersion(version_id="v-new", project_id=project_id, chapter_number=2),
        review_report=MergedReviewReport(chapter_version_id="v-new"),
        settlement=settlement,
    )
    accuracy = await mc._settlement_field_accuracy()
    assert accuracy == 1.0, f"Expected 1.0, got {accuracy}"

    # 4. 模拟 settlement 未正确应用：DB 中仍是旧值
    async with get_db() as conn:
        await conn.execute(
            "DELETE FROM character_states WHERE source_version_id = ?",
            ("v-new",),
        )
        await conn.commit()

    mc2 = MetricsCollector(
        version=ChapterVersion(version_id="v-new", project_id=project_id, chapter_number=2),
        review_report=MergedReviewReport(chapter_version_id="v-new"),
        settlement=settlement,
    )
    accuracy2 = await mc2._settlement_field_accuracy()
    assert accuracy2 == 0.0, f"Expected 0.0, got {accuracy2}"


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.asyncio
@pytest.mark.performance
async def test_single_chapter_loop_mock_under_15s(test_db, mock_call_llm) -> None:
    """mock 下单章完整闭环耗时 < 15s（含 RAG embedding，Windows 环境下放宽阈值）."""
    import time

    await reset_checkpointer()
    mock_call_llm.responses = [  # type: ignore[attr-defined]
        _goal_resp(),
        _brief_resp(),
        _writer_resp(),
        _llm_clean_resp(),
        _literary_resp(),
        _settlement_resp(),
        _summary_resp(),
    ]

    project_id = await import_seed_project("evals/seeds/xuanhuan_webnovel.json")
    await import_seed_chapter(project_id, "evals/seeds/chapters/xuanhuan_ch1.md", chapter_number=1)

    t0 = time.perf_counter()
    state = await run_chapter_pipeline(project_id=project_id, chapter_number=2, thread_id="perf-1")
    if "__interrupt__" in state:
        await resume_human_confirm("perf-1", "accept")
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    print(f"\n[performance] single chapter loop: {elapsed_ms}ms")
    assert elapsed_ms < 15000, f"Expected < 15000ms, got {elapsed_ms}ms"


@pytest.mark.performance
@pytest.mark.asyncio
@patch("songyan.workflows._nodes._index_accepted_chapter", new_callable=AsyncMock)
async def test_audit_chain_mock_under_1s(
    mock_index_chapter, test_db, mock_call_llm
) -> None:
    """mock 下 resume + settlement 耗时 < 1s（全量回归预热环境）."""
    import time

    await reset_checkpointer()
    mock_call_llm.responses = [  # type: ignore[attr-defined]
        _goal_resp(),
        _brief_resp(),
        _writer_resp(),
        _llm_clean_resp(),
        _literary_resp(),
        _settlement_resp(),
        _summary_resp(),
    ]

    project_id = await import_seed_project("evals/seeds/xuanhuan_webnovel.json")
    await import_seed_chapter(project_id, "evals/seeds/chapters/xuanhuan_ch1.md", chapter_number=1)

    state1 = await run_chapter_pipeline(project_id=project_id, chapter_number=2, thread_id="perf-2")
    assert "__interrupt__" in state1

    # 从中断恢复 accept，触发 settlement/summary
    t0 = time.perf_counter()
    await resume_human_confirm("perf-2", "accept")
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    print(f"\n[performance] resume + settlement: {elapsed_ms}ms")
    # V6 Task 149/152：settlement 后处理新增录入侧治理（demote/promote/resolve）在
    # accept 热路径上至少多做一次 setting_tracking 读取（promote 必须查历史候选），
    # 单次 get_db() 开连接含 PRAGMA quick_check ≈ +50ms。阈值从 1000ms 上调到 1500ms
    # 以覆盖该必要开销；仍足以捕捉粗粒度性能回归。
    assert elapsed_ms < 1500, f"Expected < 1500ms, got {elapsed_ms}ms"


# ---------------------------------------------------------------------------
# Integration assertions (metrics)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.performance
async def test_metrics_all_keys_present(test_db, mock_call_llm) -> None:
    """EvaluationResult.metrics 包含全部 10 个键."""
    await reset_checkpointer()
    mock_call_llm.responses = [  # type: ignore[attr-defined]
        _goal_resp(),
        _brief_resp(),
        _writer_resp(),
        _llm_clean_resp(),
        _literary_resp(),
        _settlement_resp(),
        _summary_resp(),
    ]

    result = await run_seed_project(
        project_config_path="evals/seeds/xuanhuan_webnovel.json",
        seed_chapter_path="evals/seeds/chapters/xuanhuan_ch1.md",
        output_dir="evals/output/test_metrics_keys",
        auto_accept=True,
    )

    assert result.success is True
    # 从 output_dir 读取 review_report.json 来构造 MetricsCollector
    report_path = Path(result.output_dir) / "review_report.json"
    report = MergedReviewReport.model_validate_json(report_path.read_text(encoding="utf-8"))

    # settlement 和 version 需要额外加载
    version = await ChapterVersionRepository().get(result.chapter_version_id)
    assert version is not None

    # 从 DB 重建 settlement（避免空 settlement 导致指标虚高）
    from songyan.db.connection import get_db
    from songyan.models import CharacterUpdate, NewSetting

    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT character_id, field, value FROM character_states WHERE source_version_id = ?",
            (result.chapter_version_id,),
        )
        rows = await cursor.fetchall()
        character_updates = [
            CharacterUpdate(
                character_id=r[0], field=r[1], old_value="", new_value=r[2], source_quote=""
            )
            for r in rows
        ]
        cursor = await conn.execute(
            """SELECT setting_name, description, source_quote, setting_key
            FROM setting_snapshots
            WHERE project_id = ?""",
            (result.project_id,),
        )
        rows = await cursor.fetchall()
        new_settings = [
            NewSetting(
                setting_name=r[0],
                description=r[1] or "",
                source_quote=r[2] or "",
                setting_key=r[3] or "",
            )
            for r in rows
        ]

    settlement = StateSettlement(
        character_updates=character_updates,
        new_settings=new_settings,
    )

    mc = MetricsCollector(
        version=version,
        review_report=report,
        settlement=settlement,
    )
    metrics = await mc.collect_async()

    expected_keys = {
        "pipeline_success",
        "hard_errors",
        "ai_tell_count",
        "fatigue_word_count",
        "hook_opening_pass",
        "hook_closing_pass",
        "settlement_field_accuracy",
        "setting_key_accuracy",
        "conceptual_idling_count",
        "revision_new_issues",
        "duration_ms",
    }
    assert set(metrics.keys()) == expected_keys

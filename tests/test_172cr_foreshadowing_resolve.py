"""Task 172c.r: 伏笔 resolve 机制修复 + continuity 健康度口径修复 — 单元测试.

覆盖任务书 §4.1：
- resolve 端到端（parse → validate → apply → DB resolved）
- resolve 目标为 overdue（含 dormant/archived）伏笔时同样生效
- resolve 缺 foreshadowing_id / 目标 id 不存在 → 丢弃 + warning，其余 updates 正常应用
- 未知 operation → 丢弃 + warning
- _load_current_foreshadowings 新口径：overdue 伏笔进入 prompt 事实源
- _find_overdue_foreshadowings 新口径：archived/dormant/active-overdue 全部计入
  （对齐 vdim 冻结口径）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from songyan.agents.continuity_auditor._scanners import _find_overdue_foreshadowings
from songyan.agents.settlement_extractor import (
    _build_foreshadowing_update,
    _load_current_foreshadowings,
    _validate_settlement,
    apply_settlement,
    extract_settlement,
)
from songyan.db import ProjectRepository
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import (
    ForeshadowingItem,
    ForeshadowingUpdate,
    ProjectSetting,
    StateSettlement,
)


@pytest.fixture
async def fs_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "fs172cr.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


async def _seed_project(project_id: str = "p1") -> None:
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="wuxia",
            mode_id="webnovel",
            protagonist_name="顾长风",
        ),
        project_id,
    )


async def _seed_version(
    project_id: str = "p1", version_id: str = "v1", chapter_number: int = 1
) -> None:
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO chapter_versions (
                version_id, project_id, chapter_number, version_number, version_type
            ) VALUES (?, ?, ?, ?, ?)""",
            (version_id, project_id, chapter_number, 1, "accepted"),
        )
        await conn.commit()


async def _plant(
    repo: ForeshadowingRepository,
    foreshadowing_id: str,
    *,
    status: str = "planted",
    expected_resolve_chapter: int | None = 10,
    project_id: str = "p1",
) -> None:
    await repo.create(
        ForeshadowingItem(
            foreshadowing_id=foreshadowing_id,
            description=f"伏笔-{foreshadowing_id}",
            planted_in_chapter=1,
            expected_resolve_chapter=expected_resolve_chapter,
            status=status,
        ),
        project_id,
        "v1",
    )


async def _set_lifecycle(foreshadowing_id: str, lifecycle: str) -> None:
    async with get_db() as conn:
        await conn.execute(
            "UPDATE foreshadowings SET lifecycle_status = ? WHERE foreshadowing_id = ?",
            (lifecycle, foreshadowing_id),
        )
        await conn.commit()


async def _get_status(foreshadowing_id: str) -> str:
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT status FROM foreshadowings WHERE foreshadowing_id = ?",
            (foreshadowing_id,),
        )
        row = await cursor.fetchone()
    assert row is not None
    return str(row[0])


def _resolve_llm_response(foreshadowing_id: str) -> str:
    return json.dumps(
        {
            "character_updates": [],
            "new_settings": [],
            "new_characters": [],
            "foreshadowing_updates": [
                {
                    "operation": "resolve",
                    "foreshadowing_id": foreshadowing_id,
                    "description": "本章回收",
                    "source_version_id": "v1",
                }
            ],
            "numerical_updates": [],
            "planted_hooks": [],
            "resolved_hooks": ["伏笔已回收"],
        },
        ensure_ascii=False,
    )


# =============================================================================
# Repo 层：list_overdue_unresolved（新方法，对齐 vdim 冻结口径）
# =============================================================================


class TestListOverdueUnresolved:
    async def test_includes_all_lifecycle_overdue(self, fs_db: Path) -> None:
        await _seed_project("p1")
        await _seed_version("p1")
        repo = ForeshadowingRepository()
        await _plant(repo, "fs-active-overdue", status="overdue")
        await _plant(repo, "fs-dormant-overdue", status="overdue")
        await _set_lifecycle("fs-dormant-overdue", "dormant")
        await _plant(repo, "fs-archived-overdue", status="overdue")
        await _set_lifecycle("fs-archived-overdue", "archived")

        items = await repo.list_overdue_unresolved("p1", up_to_chapter=50)
        ids = {fs.foreshadowing_id for fs in items}
        assert ids == {
            "fs-active-overdue",
            "fs-dormant-overdue",
            "fs-archived-overdue",
        }

    async def test_excludes_resolved_future_and_unknown_horizon(
        self, fs_db: Path
    ) -> None:
        await _seed_project("p1")
        await _seed_version("p1")
        repo = ForeshadowingRepository()
        await _plant(repo, "fs-resolved", status="resolved")
        await _plant(repo, "fs-future", status="planted", expected_resolve_chapter=100)
        await _plant(repo, "fs-no-horizon", status="planted", expected_resolve_chapter=None)

        items = await repo.list_overdue_unresolved("p1", up_to_chapter=50)
        assert items == []


# =============================================================================
# Scanner 口径：_find_overdue_foreshadowings（193.t 起为 operational 口径）
# =============================================================================


class TestFindOverdueForeshadowingsScope:
    async def test_counts_only_active_lifecycle_overdue(
        self, fs_db: Path
    ) -> None:
        """193.t: operational（health/streak）只计 lifecycle active 的 overdue.

        172c.r 曾要求与 vdim 冻结口径一致（archived/dormant 全计）；193.t 将
        验收门口径（five_gate 自有 SQL / vdim，仍全计）与 operational 口径显式
        分离——dormant/archived 是生命周期调度器已停放/退役条目，不再产生停
        run 的急性 P2 压力（192.ad）。全计口径的回归守护见
        TestListOverdueUnresolved 与 tests/test_193t_overdue_actionable.py。
        """
        await _seed_project("p1")
        await _seed_version("p1")
        repo = ForeshadowingRepository()
        await _plant(repo, "fs-active-overdue", status="overdue")
        await _plant(repo, "fs-dormant-overdue", status="overdue")
        await _set_lifecycle("fs-dormant-overdue", "dormant")
        await _plant(repo, "fs-archived-overdue", status="overdue")
        await _set_lifecycle("fs-archived-overdue", "archived")
        await _plant(repo, "fs-resolved", status="resolved")
        await _plant(repo, "fs-future", status="planted", expected_resolve_chapter=100)

        result = await _find_overdue_foreshadowings("p1", 50, repo)
        ids = {fs.foreshadowing_id for fs in result}
        assert ids == {"fs-active-overdue"}
        for fs in result:
            assert fs.overdue_by == 50 - 10


# =============================================================================
# Settlement prompt 事实源：overdue 伏笔对 LLM 可见
# =============================================================================


class TestLoadCurrentForeshadowings:
    async def test_includes_overdue(self, fs_db: Path) -> None:
        await _seed_project("p1")
        await _seed_version("p1")
        repo = ForeshadowingRepository()
        await _plant(repo, "fs-planted", status="planted")
        await _plant(repo, "fs-overdue", status="overdue")

        items = await _load_current_foreshadowings(repo, "p1")
        ids = {fs.foreshadowing_id for fs in items}
        assert ids == {"fs-planted", "fs-overdue"}


# =============================================================================
# Validate 层：resolve 防幻觉校验
# =============================================================================


class TestValidateResolve:
    async def test_resolve_with_known_id_kept(self) -> None:
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="resolve",
                    foreshadowing_id="fs-1",
                    description="回收",
                    source_version_id="v1",
                )
            ]
        )
        errors = await _validate_settlement(
            settlement,
            "正文",
            [],
            [],
            chapter_number=12,
            project_id="p1",
            resolvable_foreshadowing_ids={"fs-1"},
        )
        assert errors == []
        assert len(settlement.foreshadowing_updates) == 1

    async def test_resolve_with_unknown_id_dropped_with_warning(self) -> None:
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="resolve",
                    foreshadowing_id="fs-ghost",
                    description="幻觉回收",
                    source_version_id="v1",
                ),
                ForeshadowingUpdate(
                    operation="plant",
                    description="正常埋设",
                    source_version_id="v1",
                ),
            ]
        )
        with capture_logs() as logs:
            errors = await _validate_settlement(
                settlement,
                "正文",
                [],
                [],
                chapter_number=12,
                project_id="p1",
                resolvable_foreshadowing_ids={"fs-1"},
            )
        # 幻觉 resolve 被丢弃但不阻断整单结算；plant 保留
        assert errors == []
        remaining = [fs.operation for fs in settlement.foreshadowing_updates]
        assert remaining == ["plant"]
        assert any(
            log.get("event") == "settlement.foreshadowing_resolve_unknown_id"
            and log.get("log_level") == "warning"
            for log in logs
        )

    async def test_resolve_with_missing_id_dropped_with_warning(self) -> None:
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="resolve",
                    foreshadowing_id=None,
                    description="缺 id 回收",
                    source_version_id="v1",
                )
            ]
        )
        with capture_logs() as logs:
            errors = await _validate_settlement(
                settlement,
                "正文",
                [],
                [],
                chapter_number=12,
                project_id="p1",
                resolvable_foreshadowing_ids={"fs-1"},
            )
        assert errors == []
        assert settlement.foreshadowing_updates == []
        assert any(
            log.get("event") == "settlement.foreshadowing_resolve_missing_id"
            and log.get("log_level") == "warning"
            for log in logs
        )


# =============================================================================
# 静默丢弃点补日志
# =============================================================================


class TestSilentDropLogging:
    def test_build_unknown_operation_logs_warning(self) -> None:
        with capture_logs() as logs:
            result = _build_foreshadowing_update({"operation": "bogus"})
        assert result is None
        assert any(
            log.get("event") == "settlement.parse.foreshadowing_unknown_operation"
            and log.get("log_level") == "warning"
            for log in logs
        )

    async def test_apply_resolve_missing_id_logs_warning_and_skips(self) -> None:
        from unittest.mock import AsyncMock

        mock_fs = AsyncMock()
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="resolve",
                    foreshadowing_id=None,
                    description="缺 id 回收",
                    source_version_id="v1",
                )
            ]
        )
        with capture_logs() as logs:
            await apply_settlement(
                settlement,
                "p1",
                12,
                "v1",
                conn=AsyncMock(),
                char_repo=AsyncMock(),
                setting_repo=AsyncMock(),
                foreshadowing_repo=mock_fs,
                numerical_repo=AsyncMock(),
            )
        mock_fs.update_status.assert_not_called()
        assert any(
            log.get("event") == "settlement.foreshadowing_resolve_missing_id"
            and log.get("log_level") == "warning"
            for log in logs
        )


# =============================================================================
# 端到端：extract → validate → apply → DB resolved
# =============================================================================


class TestResolveEndToEnd:
    async def test_resolve_planted_foreshadowing(self, fs_db: Path) -> None:
        await _seed_project("p1")
        await _seed_version("p1")
        repo = ForeshadowingRepository()
        await _plant(repo, "fs-1", status="planted")

        from unittest.mock import patch

        with patch(
            "songyan.agents.settlement_extractor.call_llm",
            return_value=_resolve_llm_response("fs-1"),
        ):
            result = await extract_settlement(
                content="正文中回收了伏笔。",
                project_id="p1",
                chapter_number=12,
                version_id="v1",
            )

        assert result.validation_status == "valid"
        resolves = [
            fs for fs in result.foreshadowing_updates if fs.operation == "resolve"
        ]
        assert len(resolves) == 1
        assert resolves[0].foreshadowing_id == "fs-1"

        async with get_db() as conn:
            await apply_settlement(result, "p1", 12, "v1", conn=conn)
            await conn.commit()

        assert await _get_status("fs-1") == "resolved"

    async def test_resolve_overdue_foreshadowing(self, fs_db: Path) -> None:
        """overdue 伏笔必须同时：(a) 进入 prompt 事实源；(b) 通过 resolve 校验；
        (c) 落库 resolved."""
        await _seed_project("p1")
        await _seed_version("p1")
        repo = ForeshadowingRepository()
        await _plant(repo, "fs-2", status="overdue", expected_resolve_chapter=5)

        from unittest.mock import patch

        with patch(
            "songyan.agents.settlement_extractor.call_llm",
            return_value=_resolve_llm_response("fs-2"),
        ) as mock_llm:
            result = await extract_settlement(
                content="正文中回收了逾期伏笔。",
                project_id="p1",
                chapter_number=12,
                version_id="v1",
            )

        # (a) overdue 伏笔出现在发给 LLM 的 prompt 事实源中
        prompt_arg = mock_llm.call_args[0][0]
        assert "fs-2" in prompt_arg

        assert result.validation_status == "valid"
        resolves = [
            fs for fs in result.foreshadowing_updates if fs.operation == "resolve"
        ]
        assert len(resolves) == 1

        async with get_db() as conn:
            await apply_settlement(result, "p1", 12, "v1", conn=conn)
            await conn.commit()

        assert await _get_status("fs-2") == "resolved"

    async def test_resolve_dormant_foreshadowing_applies(self, fs_db: Path) -> None:
        """dormant/archived 伏笔的 resolve 直接落库（update_status 不按 lifecycle 过滤）."""
        await _seed_project("p1")
        await _seed_version("p1")
        repo = ForeshadowingRepository()
        await _plant(repo, "fs-3", status="overdue", expected_resolve_chapter=5)
        await _set_lifecycle("fs-3", "dormant")

        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="resolve",
                    foreshadowing_id="fs-3",
                    description="回收 dormant 伏笔",
                    source_version_id="v1",
                )
            ]
        )
        async with get_db() as conn:
            await apply_settlement(settlement, "p1", 12, "v1", conn=conn)
            await conn.commit()

        assert await _get_status("fs-3") == "resolved"

"""task 269 切片1：canon pending / confirm batch / dismiss batch 分组过滤 CLI。

口径：--chapter N 匹配 attribute 的 valid_from_ch == N；entity 经「被过滤后
attribute 引用」入选。非 TTY 无 --yes exit 2 零写入；空集 exit 0 明示；
confirm batch 无过滤 = 全部 pending（259 行为不变）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import ProjectRepository
from songyan.models.plan_facts import PlanAttribute, PlanEntity
from songyan.models.project import ProjectSetting

_PROJECT = "p-pending-groups"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def pending_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "pending-groups.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="urban",
            mode_id="webnovel",
            protagonist_name="陈屿",
            title="pending groups",
        ),
        _PROJECT,
    )
    repo = PlanFactRepository()
    # e1+e2：人写 pending（canon edit 同形）；e3：extract 提案
    await repo.write_entity(
        PlanEntity(
            entity_id="e1", project_id=_PROJECT, entity_type="person",
            approval_status="pending",
        )
    )
    await repo.write_entity(
        PlanEntity(
            entity_id="e2", project_id=_PROJECT, entity_type="item",
            approval_status="pending",
        )
    )
    await repo.write_entity(
        PlanEntity(
            entity_id="e3", project_id=_PROJECT, entity_type="person",
            approval_status="pending",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="a-ch2-human", project_id=_PROJECT, entity_id="e1",
            key="职位", value="学徒", valid_from_ch=2, source="human",
            approval_status="pending",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="a-ch3-human", project_id=_PROJECT, entity_id="e2",
            key="位置", value="网吧", valid_from_ch=3, source="human",
            approval_status="pending",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="a-ch2-extract", project_id=_PROJECT, entity_id="e3",
            key="状态", value="焦虑", valid_from_ch=2, source="extract",
            approval_status="pending",
        )
    )
    return db_path


def _pending(runner: CliRunner, *extra: str) -> dict:
    result = runner.invoke(cli, ["canon", "pending", "--project-id", _PROJECT, *extra, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


class TestPendingFilter:
    def test_chapter_filter(self, runner: CliRunner, pending_db: Path) -> None:
        payload = _pending(runner, "--chapter", "2")
        assert {a["attribute_id"] for a in payload["attributes"]} == {
            "a-ch2-human",
            "a-ch2-extract",
        }
        assert {e["entity_id"] for e in payload["entities"]} == {"e1", "e3"}

    def test_chapter_and_source(self, runner: CliRunner, pending_db: Path) -> None:
        payload = _pending(runner, "--chapter", "2", "--source", "extract")
        assert [a["attribute_id"] for a in payload["attributes"]] == ["a-ch2-extract"]
        assert [e["entity_id"] for e in payload["entities"]] == ["e3"]

    def test_unfiltered_lists_all(self, runner: CliRunner, pending_db: Path) -> None:
        payload = _pending(runner)
        assert len(payload["entities"]) == 3
        assert len(payload["attributes"]) == 3

    def test_text_output_groups_by_chapter(
        self, runner: CliRunner, pending_db: Path
    ) -> None:
        result = runner.invoke(cli, ["canon", "pending", "--project-id", _PROJECT])
        assert result.exit_code == 0, result.output
        # 未过滤文本按章分节
        assert "ch 2" in result.output
        assert "ch 3" in result.output


class TestConfirmBatchFilter:
    def test_confirm_chapter_scope(self, runner: CliRunner, pending_db: Path) -> None:
        result = runner.invoke(
            cli,
            ["canon", "confirm", "batch", "--project-id", _PROJECT, "--chapter", "2", "--yes"],
        )
        assert result.exit_code == 0, result.output
        payload = _pending(runner)
        # ch2 两 attribute 已确认；ch3 与人写 entity e2 相关行保留
        remaining_attrs = {a["attribute_id"] for a in payload["attributes"]}
        assert "a-ch3-human" in remaining_attrs
        assert "a-ch2-human" not in remaining_attrs
        assert "a-ch2-extract" not in remaining_attrs

    def test_empty_scope_exit_0_no_write(
        self, runner: CliRunner, pending_db: Path
    ) -> None:
        result = runner.invoke(
            cli,
            ["canon", "confirm", "batch", "--project-id", _PROJECT, "--chapter", "9", "--yes"],
        )
        assert result.exit_code == 0, result.output
        assert "无" in result.output
        assert len(_pending(runner)["attributes"]) == 3

    def test_non_tty_without_yes_exit_2_zero_write(
        self, runner: CliRunner, pending_db: Path
    ) -> None:
        result = runner.invoke(
            cli, ["canon", "confirm", "batch", "--project-id", _PROJECT, "--chapter", "2"]
        )
        assert result.exit_code == 2
        assert len(_pending(runner)["attributes"]) == 3

    def test_unfiltered_batch_still_confirms_all(
        self, runner: CliRunner, pending_db: Path
    ) -> None:
        """259 兼容：无过滤 batch = 全部 pending。"""
        result = runner.invoke(
            cli, ["canon", "confirm", "batch", "--project-id", _PROJECT, "--yes"]
        )
        assert result.exit_code == 0, result.output
        payload = _pending(runner)
        assert payload["entities"] == [] and payload["attributes"] == []


class TestDismissBatch:
    def test_dismiss_chapter_scope(self, runner: CliRunner, pending_db: Path) -> None:
        result = runner.invoke(
            cli,
            ["canon", "dismiss", "batch", "--project-id", _PROJECT, "--chapter", "2", "--yes"],
        )
        assert result.exit_code == 0, result.output
        payload = _pending(runner)
        remaining_attrs = {a["attribute_id"] for a in payload["attributes"]}
        assert remaining_attrs == {"a-ch3-human"}

    def test_dismiss_non_tty_exit_2(self, runner: CliRunner, pending_db: Path) -> None:
        result = runner.invoke(
            cli, ["canon", "dismiss", "batch", "--project-id", _PROJECT, "--chapter", "2"]
        )
        assert result.exit_code == 2
        assert len(_pending(runner)["attributes"]) == 3

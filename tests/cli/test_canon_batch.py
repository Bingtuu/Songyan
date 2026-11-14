"""task 259：``canon pending`` 列出 + ``canon confirm batch`` 批量确认。

批量仍是显式人写径：摘要 y/N / --yes / 非 TTY 拒绝（B4 同形）。
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

_PROJECT = "p-batch"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def batch_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "canon-batch.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="batch",
        ),
        _PROJECT,
    )
    repo = PlanFactRepository()
    for i in range(2):
        await repo.write_entity(
            PlanEntity(
                entity_id=f"ent-p{i}",
                project_id=_PROJECT,
                entity_type="person",
                aliases=[f"角色{i}"],
                approval_status="pending",
            )
        )
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-ok",
            project_id=_PROJECT,
            entity_type="prop",
            aliases=["已批准"],
            approval_status="approved",
        )
    )
    for i in range(2):
        await repo.write_attribute(
            PlanAttribute(
                attribute_id=f"attr-p{i}",
                project_id=_PROJECT,
                entity_id="ent-ok",
                key=f"key{i}",
                value=f"值{i}",
                source="extract",
                approval_status="pending",
            )
        )
    return db_path


def _approved_counts() -> tuple[int, int]:
    import asyncio

    async def _q() -> tuple[int, int]:
        repo = PlanFactRepository()
        ents = await repo.list_canon_entities(_PROJECT)
        attrs = await repo.list_canon_attributes(_PROJECT)
        return len(ents), len(attrs)

    return asyncio.run(_q())


class TestPending:
    def test_pending_json_lists_only_pending(
        self, runner: CliRunner, batch_db: Path
    ) -> None:
        result = runner.invoke(
            cli, ["canon", "pending", "--project-id", _PROJECT, "--json"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert {e["entity_id"] for e in payload["entities"]} == {
            "ent-p0",
            "ent-p1",
        }
        assert {a["attribute_id"] for a in payload["attributes"]} == {
            "attr-p0",
            "attr-p1",
        }
        assert payload["attributes"][0]["key"].startswith("key")

    def test_pending_text_shows_preview(
        self, runner: CliRunner, batch_db: Path
    ) -> None:
        result = runner.invoke(cli, ["canon", "pending", "--project-id", _PROJECT])
        assert result.exit_code == 0, result.output
        assert "ent-p0" in result.output
        assert "key0=值0" in result.output


class TestBatch:
    def test_batch_yes_confirms_all(
        self, runner: CliRunner, batch_db: Path
    ) -> None:
        result = runner.invoke(
            cli,
            ["canon", "confirm", "batch", "--project-id", _PROJECT, "--yes"],
        )
        assert result.exit_code == 0, result.output
        assert "entity=2" in result.output
        assert "attribute=2" in result.output
        ents, attrs = _approved_counts()
        assert ents == 3  # 2 pending + 原 approved
        assert attrs == 2

    def test_batch_interactive_accept(
        self, runner: CliRunner, batch_db: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import songyan.cli.commands.canon_write as canon_mod

        monkeypatch.setattr(canon_mod, "_stdin_isatty", lambda: True)
        result = runner.invoke(
            cli,
            ["canon", "confirm", "batch", "--project-id", _PROJECT],
            input="y\n",
        )
        assert result.exit_code == 0, result.output
        _, attrs = _approved_counts()
        assert attrs == 2

    def test_batch_interactive_decline_zero_writes(
        self, runner: CliRunner, batch_db: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import songyan.cli.commands.canon_write as canon_mod

        monkeypatch.setattr(canon_mod, "_stdin_isatty", lambda: True)
        result = runner.invoke(
            cli,
            ["canon", "confirm", "batch", "--project-id", _PROJECT],
            input="n\n",
        )
        assert result.exit_code == 2
        ents, attrs = _approved_counts()
        assert ents == 1  # 只有原 approved
        assert attrs == 0

    def test_batch_non_tty_requires_yes(
        self, runner: CliRunner, batch_db: Path
    ) -> None:
        result = runner.invoke(
            cli, ["canon", "confirm", "batch", "--project-id", _PROJECT]
        )
        assert result.exit_code == 2
        assert "--yes" in result.stderr

    def test_batch_empty_pending_exit_0(
        self, runner: CliRunner, batch_db: Path
    ) -> None:
        first = runner.invoke(
            cli,
            ["canon", "confirm", "batch", "--project-id", _PROJECT, "--yes"],
        )
        assert first.exit_code == 0
        again = runner.invoke(
            cli,
            ["canon", "confirm", "batch", "--project-id", _PROJECT, "--yes"],
        )
        assert again.exit_code == 0
        assert "无 pending" in again.output

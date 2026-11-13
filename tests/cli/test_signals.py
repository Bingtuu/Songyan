"""task 257：S 信号度量面——edit_ratio 落表 + `songyan signals`（tech-post-m4 v2 §B）。

口径映射见 docs/tech-post-m4.md §B.2；每信号注明数据源。S2 冲突关闭周期
现网无记账面 → 显式 gap，不编造。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.project import ProjectSetting
from songyan.models.variant import ChapterVariant

_PROJECT = "p-signals"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def signals_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "signals.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="signals",
            words_per_chapter=3000,
        ),
        _PROJECT,
    )

    versions = ChapterVersionRepository()
    heads = ChapterHeadRepository()
    variants = ChapterVariantRepository()

    # S1 构造数据：窗口内 1 条 approved（updated_at=now）、窗口外 1 条、rejected 1 条
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO plan_entities (entity_id, project_id, entity_type, aliases, "
        "approval_status, created_at, updated_at) VALUES "
        "('e-win', ?, 'person', '[]', 'approved', datetime('now'), datetime('now'))",
        (_PROJECT,),
    )
    con.execute(
        "INSERT INTO plan_entities (entity_id, project_id, entity_type, aliases, "
        "approval_status, created_at, updated_at) VALUES "
        "('e-old', ?, 'person', '[]', 'approved', datetime('now','-30 days'), "
        "datetime('now','-30 days'))",
        (_PROJECT,),
    )
    con.execute(
        "INSERT INTO plan_entities (entity_id, project_id, entity_type, aliases, "
        "approval_status, created_at, updated_at) VALUES "
        "('e-rej', ?, 'prop', '[]', 'rejected', datetime('now'), datetime('now'))",
        (_PROJECT,),
    )
    con.commit()
    con.close()

    async def _settled(ch: int, edit_ratio_col: float | None) -> None:
        vid = f"ver-s{ch}"
        aid = f"ver-s{ch}-acc"
        await versions.create(
            ChapterVersion(
                version_id=vid,
                project_id=_PROJECT,
                chapter_number=ch,
                version_number=1,
                version_type="draft",
                content="正文" * 80,
                word_count=160,
            )
        )
        await versions.create(
            ChapterVersion(
                version_id=aid,
                project_id=_PROJECT,
                chapter_number=ch,
                version_number=2,
                version_type="accepted",
                content="正文" * 80,
                word_count=160,
                parent_version_id=vid,
            )
        )
        await heads.update(
            ChapterHead(
                project_id=_PROJECT,
                chapter_number=ch,
                current_version_id=aid,
                accepted_version_id=aid,
                status="accepted",
            )
        )
        if edit_ratio_col is not None:
            await heads.set_edit_ratio(_PROJECT, ch, edit_ratio_col)

    await _settled(1, 0.0)
    await _settled(2, 0.5)
    await _settled(3, None)  # 旧行：NULL = 未记

    # S4：两个 picked 槽（1 号与 2 号各一）
    for i, slot in enumerate((1, 2), start=1):
        vid = f"ver-p{i}"
        await versions.create(
            ChapterVersion(
                version_id=vid,
                project_id=_PROJECT,
                chapter_number=10 + i,
                version_number=1,
                version_type="draft",
                content="稿" * 120,
                word_count=240,
            )
        )
        await variants.insert(
            ChapterVariant(
                variant_id=f"var-p{i}",
                project_id=_PROJECT,
                chapter_number=10 + i,
                slot_index=slot,
                status="picked",
                parent_canon_fingerprint="fp",
                content_ref=vid,
                cost_cny_estimate=0.01 * i,
                created_at="2026-11-13T00:00:00Z",
                updated_at="2026-11-13T00:00:00Z",
            )
        )

    # S3：三条未 resolved 伏笔（planted_in_chapter 1/2/5）
    con = sqlite3.connect(db_path)
    for i, planted in enumerate((1, 2, 5), start=1):
        con.execute(
            "INSERT INTO foreshadowings (foreshadowing_id, project_id, description, "
            "planted_in_chapter, status, source_version_id) VALUES (?,?,?,?,?,?)",
            (f"fs-{i}", _PROJECT, f"伏笔{i}", planted, "planted", "ver-s1"),
        )
    con.commit()
    con.close()

    # S7：费用遥测（ch1 两笔 0.01+0.02，ch2 一笔 0.04）
    from songyan.db.llm_call_usage_repo import LlmCallUsageRepository

    usage = LlmCallUsageRepository()
    for ch, cost in ((1, 0.01), (1, 0.02), (2, 0.04)):
        await usage.record(
            model="mock",
            token_source="estimate",
            cost_source="pricing_estimate",
            project_id=_PROJECT,
            chapter_number=ch,
            agent="writer",
            cost_cny=cost,
        )
    return db_path


class TestEditRatioColumn:
    def test_column_written_and_read(self, runner: CliRunner, signals_db: Path) -> None:
        con = sqlite3.connect(signals_db)
        rows = dict(
            con.execute(
                "SELECT chapter_number, edit_ratio FROM chapter_heads "
                "WHERE project_id=? ORDER BY chapter_number",
                (_PROJECT,),
            ).fetchall()
        )
        con.close()
        assert rows[1] == 0.0
        assert rows[2] == 0.5
        assert rows[3] is None

    def test_chapter_status_reads_column(
        self, runner: CliRunner, signals_db: Path
    ) -> None:
        result = runner.invoke(
            cli,
            [
                "chapter", "status",
                "--project-id", _PROJECT,
                "--chapter", "2", "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["edit_ratio"] == 0.5


class TestSignalsCommand:
    def _payload(self, runner: CliRunner) -> dict:
        result = runner.invoke(
            cli, ["signals", "--project-id", _PROJECT, "--json"]
        )
        assert result.exit_code == 0, result.output
        return json.loads(result.stdout)

    def test_s1_confirms_and_dismiss_ratio(
        self, runner: CliRunner, signals_db: Path
    ) -> None:
        payload = self._payload(runner)
        s1 = payload["signals"]["S1"]
        assert s1["weekly_confirms"] == 1  # 仅 e-win 落在 7 天窗口
        assert s1["dismiss_ratio"] == pytest.approx(1 / 3, abs=1e-4)  # 实现侧 4 位舍入

    def test_s3_foreshadow_age_p50(
        self, runner: CliRunner, signals_db: Path
    ) -> None:
        payload = self._payload(runner)
        s3 = payload["signals"]["S3"]
        # 当前进度章 = 3；未 resolved 伏笔 planted 1/2/5 → 年龄 2/1/-2（负值 clamp 0）→ 中位数 1
        assert s3["open_count"] == 3
        assert s3["age_p50"] == 1

    def test_s4_pick_distribution(self, runner: CliRunner, signals_db: Path) -> None:
        payload = self._payload(runner)
        s4 = payload["signals"]["S4"]
        assert s4["picks_total"] == 2
        assert s4["slots"] == {"1": 1, "2": 1}
        assert s4["collapse_warning"] is False

    def test_s5_edit_ratio_distribution(
        self, runner: CliRunner, signals_db: Path
    ) -> None:
        payload = self._payload(runner)
        s5 = payload["signals"]["S5"]
        assert s5["count"] == 2  # NULL 不计入
        assert s5["null_count"] == 1
        assert s5["low_edit_share"] == 0.5  # 0.0 < 5% 占一半

    def test_s7_cost_per_chapter(self, runner: CliRunner, signals_db: Path) -> None:
        payload = self._payload(runner)
        s7 = payload["signals"]["S7"]
        assert s7["total_cost_cny"] == pytest.approx(0.07)
        assert s7["settled_chapters"] == 3
        assert s7["per_chapter"] == {"1": 0.03, "2": 0.04}
        assert s7["mean_per_settled_chapter"] == pytest.approx(0.07 / 3, abs=1e-4)

    def test_s2_gap_marked(self, runner: CliRunner, signals_db: Path) -> None:
        payload = self._payload(runner)
        assert payload["signals"]["S2"]["gap"] is True

    def test_text_output_sections(self, runner: CliRunner, signals_db: Path) -> None:
        result = runner.invoke(cli, ["signals", "--project-id", _PROJECT])
        assert result.exit_code == 0, result.output
        for key in ("S1", "S2", "S3", "S4", "S5", "S7"):
            assert key in result.output
        assert "gap" in result.output

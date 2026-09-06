"""Task 229: CLI 质量口径复现命令（five-gate / t9）测试."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.models import ProjectSetting

_PROJECT_ID = "cli-quality-project"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _write_baseline(path: Path) -> Path:
    """单点 baseline：阈值宽松，便于构造 PASS/FAIL 用例."""
    baseline = {
        "baseline_id": "test_fixture_baseline",
        "points": [
            {
                "up_to": 1,
                "accepted": 1,
                "budget_used_peak": 0.99,
                "overdue_foreshadowing": 1.0,
                "health_latest": 9.0,
                "ced_per_1k_words": 1.0,
            }
        ],
    }
    path.write_text(json.dumps(baseline, ensure_ascii=False), encoding="utf-8")
    return path


def _insert_version_and_head(
    db_path: Path,
    *,
    content: str,
    with_consistency_issue: bool = False,
    health: float | None = 9.0,
) -> None:
    """直接 SQL 插入最小 accepted 章数据（fixture 专用）."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chapter_versions (version_id, project_id, chapter_number,"
            " version_number, version_type, content) VALUES (?, ?, 1, 1, 'accepted', ?)",
            ("v-fixture-1", _PROJECT_ID, content),
        )
        cur.execute(
            "INSERT INTO chapter_heads (project_id, chapter_number, current_version_id,"
            " accepted_version_id, status) VALUES (?, 1, 'v-fixture-1', 'v-fixture-1', 'accepted')",
            (_PROJECT_ID,),
        )
        if with_consistency_issue:
            issues = [
                {
                    "issue_id": "issue-1",
                    "severity": "major",
                    "category": "world_consistency",
                    "evidence_quote": "正文证据句",
                }
            ]
            cur.execute(
                "INSERT INTO review_reports (report_id, chapter_version_id, audit_type, issues)"
                " VALUES ('rr-1', 'v-fixture-1', 'merged', ?)",
                (json.dumps(issues, ensure_ascii=False),),
            )
        if health is not None:
            cur.execute(
                "INSERT INTO continuity_reports (report_id, project_id, checked_up_to_chapter,"
                " overall_health_score) VALUES ('cr-1', ?, 1, ?)",
                (_PROJECT_ID, health),
            )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
async def quality_cli_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "cli-quality.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            title="CLI 质量口径项目",
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="林远",
        ),
        _PROJECT_ID,
    )
    return db_path


# --------------------------------------------------------------------------- #
# five-gate
# --------------------------------------------------------------------------- #


def test_five_gate_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["five-gate", "--help"])

    assert result.exit_code == 0
    assert "--project-id" in result.output
    assert "--up-to" in result.output


def test_five_gate_missing_db_exit_2(runner: CliRunner, tmp_path: Path) -> None:
    missing = tmp_path / "missing.db"
    result = runner.invoke(
        cli,
        ["five-gate", "--project-id", _PROJECT_ID, "--up-to", "1", "--db", str(missing)],
    )

    assert result.exit_code == 2
    assert "five-gate error" in result.output


async def test_five_gate_pass_exit_0(
    runner: CliRunner, quality_cli_db: Path, tmp_path: Path
) -> None:
    _insert_version_and_head(quality_cli_db, content="第一章的正文内容。")
    baseline = _write_baseline(tmp_path / "baseline.json")

    result = runner.invoke(
        cli,
        [
            "five-gate",
            "--project-id",
            _PROJECT_ID,
            "--up-to",
            "1",
            "--baseline",
            str(baseline),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "gate verdict: PASS" in result.output
    # --genre 缺省时从 projects 表解析
    assert "scifi" in result.output


async def test_five_gate_fail_exit_1(
    runner: CliRunner, quality_cli_db: Path, tmp_path: Path
) -> None:
    _insert_version_and_head(quality_cli_db, content="第一章的正文内容。", health=7.0)
    baseline = _write_baseline(tmp_path / "baseline.json")

    result = runner.invoke(
        cli,
        [
            "five-gate",
            "--project-id",
            _PROJECT_ID,
            "--up-to",
            "1",
            "--baseline",
            str(baseline),
        ],
    )

    assert result.exit_code == 1, result.output
    assert "gate verdict: FAIL" in result.output


async def test_five_gate_json_contains_ced(
    runner: CliRunner, quality_cli_db: Path, tmp_path: Path
) -> None:
    """CED 独立取数（R2）：--format json 的 metrics.ced 段."""
    _insert_version_and_head(
        quality_cli_db, content="第一章的正文内容。", with_consistency_issue=True
    )
    baseline = _write_baseline(tmp_path / "baseline.json")

    result = runner.invoke(
        cli,
        [
            "five-gate",
            "--project-id",
            _PROJECT_ID,
            "--up-to",
            "1",
            "--baseline",
            str(baseline),
            "--format",
            "json",
        ],
    )

    # 微小字数下 1 个 consistency issue 必然破 CED 门 → exit 1
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["metrics"]["ced"]["issue_count"] == 1
    assert payload["metrics"]["ced"]["word_count"] > 0
    assert payload["metrics"]["ced"]["ced_per_1k_words"] > 0


async def test_five_gate_readonly_db_file(
    runner: CliRunner, quality_cli_db: Path, tmp_path: Path
) -> None:
    """只读性证明：DB 文件置为只读后命令仍正常工作."""
    _insert_version_and_head(quality_cli_db, content="第一章的正文内容。")
    baseline = _write_baseline(tmp_path / "baseline.json")
    os.chmod(quality_cli_db, 0o444)
    try:
        result = runner.invoke(
            cli,
            [
                "five-gate",
                "--project-id",
                _PROJECT_ID,
                "--up-to",
                "1",
                "--baseline",
                str(baseline),
            ],
        )
        assert result.exit_code == 0, result.output
    finally:
        os.chmod(quality_cli_db, 0o644)


# --------------------------------------------------------------------------- #
# t9
# --------------------------------------------------------------------------- #


def test_t9_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["t9", "--help"])

    assert result.exit_code == 0
    assert "--project-id" in result.output
    assert "--chapters" in result.output


def test_t9_clean_pass_exit_0(runner: CliRunner, quality_cli_db: Path) -> None:
    _insert_version_and_head(quality_cli_db, content="第一章的正文内容。\n\n第二段继续叙事。")

    result = runner.invoke(cli, ["t9", "--project-id", _PROJECT_ID, "--chapters", "1-1"])

    assert result.exit_code == 0, result.output
    assert "PASS" in result.output
    # persist=False 证明：派生表无写入
    conn = sqlite3.connect(quality_cli_db)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM text_cleanliness_metrics WHERE project_id = ?",
            (_PROJECT_ID,),
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 0


def test_t9_meta_leak_fail_exit_1(runner: CliRunner, quality_cli_db: Path) -> None:
    _insert_version_and_head(quality_cli_db, content="他在甲 / 乙两条路之间停下。")

    result = runner.invoke(cli, ["t9", "--project-id", _PROJECT_ID, "--chapters", "1"])

    assert result.exit_code == 1, result.output
    assert "FAIL" in result.output


def test_t9_insufficient_exit_2(runner: CliRunner, quality_cli_db: Path) -> None:
    """无 accepted 正文时样本不足，不允许以 0 退出."""
    result = runner.invoke(cli, ["t9", "--project-id", _PROJECT_ID, "--chapters", "1-3"])

    assert result.exit_code == 2, result.output

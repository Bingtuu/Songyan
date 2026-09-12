"""Task 235: songyan import CLI 测试."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from songyan.cli.main import cli

SAMPLE = (
    "第一章 风起\n\n松烟初入城。\n\n"
    "第二章\n\n雨下了一夜。\n"
)


def _make_source(tmp_path: Path) -> Path:
    src = tmp_path / "book.txt"
    src.write_text(SAMPLE, encoding="utf-8")
    return src


def test_segment_confirm_status_flow(tmp_path: Path) -> None:
    runner = CliRunner()
    src = _make_source(tmp_path)
    out = tmp_path / "import-out"

    result = runner.invoke(cli, ["import", "segment", "--source", str(src), "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert "章节数" in result.output and ": 2" in result.output

    manifest = out / "manifest.json"
    result = runner.invoke(cli, ["import", "status", "--manifest", str(manifest)])
    assert result.exit_code == 1  # 未确认

    result = runner.invoke(cli, ["import", "confirm", "--manifest", str(manifest)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["import", "status", "--manifest", str(manifest)])
    assert result.exit_code == 0


def test_segment_missing_source_fails(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "import", "segment",
            "--source", str(tmp_path / "none.txt"),
            "--output", str(tmp_path / "o"),
        ],
    )
    assert result.exit_code != 0


def test_segment_no_chapter_header_fails(tmp_path: Path) -> None:
    runner = CliRunner()
    src = tmp_path / "plain.txt"
    src.write_text("没有任何章节标题。" * 50, encoding="utf-8")
    result = runner.invoke(
        cli,
        ["import", "segment", "--source", str(src), "--output", str(tmp_path / "o")],
    )
    assert result.exit_code != 0
    assert "章节标题" in result.output

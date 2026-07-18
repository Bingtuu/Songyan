from __future__ import annotations

import json
import logging

import pytest
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from songyan.utils.logging_setup import configure_logging, flush_logging_handlers


@pytest.fixture(autouse=True)
def _restore_logging_state():
    """configure_logging 修改 root logger/structlog 全局状态，测试后必须恢复."""
    root_logger = logging.getLogger()
    old_level = root_logger.level
    clear_contextvars()
    yield
    flush_logging_handlers(close=True)
    root_logger.setLevel(old_level)
    structlog.reset_defaults()
    clear_contextvars()


def _read_jsonl(path):
    flush_logging_handlers()
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_warning_console_filters_info_but_file_keeps_debug(tmp_path, capsys) -> None:
    log_file = configure_logging("WARNING", log_dir=tmp_path, file_level="DEBUG")
    logger = structlog.get_logger("tests.logging")

    logger.debug("debug_event")
    logger.info("info_event")
    logger.warning("warning_event")

    captured = capsys.readouterr()
    assert "info_event" not in captured.err
    assert "debug_event" not in captured.err
    assert "warning_event" in captured.err

    events = {row["event"] for row in _read_jsonl(log_file)}
    assert {"debug_event", "info_event", "warning_event"} <= events
    flush_logging_handlers(close=True)


def test_configure_logging_is_idempotent(tmp_path) -> None:
    configure_logging("INFO", log_dir=tmp_path)
    configure_logging("INFO", log_dir=tmp_path)

    managed = [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_songyan_managed_handler", False)
    ]
    assert len(managed) == 2
    flush_logging_handlers(close=True)


def test_contextvars_are_written_to_jsonl(tmp_path) -> None:
    clear_contextvars()
    log_file = configure_logging("INFO", log_dir=tmp_path)
    bind_contextvars(run_id="run-1", chapter_number=3, db_path="songyan.db")

    structlog.get_logger("tests.logging").info("context_event")

    rows = _read_jsonl(log_file)
    row = next(item for item in rows if item["event"] == "context_event")
    assert row["run_id"] == "run-1"
    assert row["chapter_number"] == 3
    assert row["db_path"] == "songyan.db"
    clear_contextvars()
    flush_logging_handlers(close=True)


def test_node_rebind_contextvars_keeps_run_id(tmp_path) -> None:
    clear_contextvars()
    log_file = configure_logging("INFO", log_dir=tmp_path)

    def simulated_node(state: dict[str, object]) -> None:
        bind_contextvars(
            run_id=state["run_id"],
            chapter_number=state["chapter_number"],
            stage="writer",
        )
        structlog.get_logger("tests.node").info("node_event")

    simulated_node({"run_id": "run-node", "chapter_number": 7})

    row = next(item for item in _read_jsonl(log_file) if item["event"] == "node_event")
    assert row["run_id"] == "run-node"
    assert row["chapter_number"] == 7
    assert row["stage"] == "writer"
    clear_contextvars()
    flush_logging_handlers(close=True)


def test_third_party_loggers_are_warning(tmp_path) -> None:
    configure_logging("INFO", log_dir=tmp_path)

    assert logging.getLogger("LiteLLM").level == logging.WARNING
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("litellm").level == logging.WARNING
    assert logging.getLogger("langchain").level == logging.WARNING
    flush_logging_handlers(close=True)


def test_jsonl_file_contains_valid_json_lines(tmp_path) -> None:
    log_file = configure_logging("INFO", log_dir=tmp_path)
    structlog.get_logger("tests.logging").info("json_event", answer=42)

    rows = _read_jsonl(log_file)
    row = next(item for item in rows if item["event"] == "json_event")
    assert row["answer"] == 42
    assert row["level"] == "info"
    flush_logging_handlers(close=True)

"""Application logging setup for CLI and long-running harnesses."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Final, cast

import structlog

_MANAGED_HANDLER_ATTR: Final = "_songyan_managed_handler"
_THIRD_PARTY_LOGGERS: Final = (
    "LiteLLM",
    "litellm",
    "httpx",
    "httpcore",
    "asyncio",
    "langchain",
    "langgraph",
)


def _coerce_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    normalized = level.upper()
    value = logging.getLevelName(normalized)
    if isinstance(value, int):
        return value
    raise ValueError(f"Invalid logging level: {level!r}")


def _managed_handlers(root_logger: logging.Logger) -> list[logging.Handler]:
    return [
        handler
        for handler in root_logger.handlers
        if getattr(handler, _MANAGED_HANDLER_ATTR, False)
    ]


def configure_logging(
    log_level: str = "INFO",
    *,
    log_dir: Path = Path("logs/app"),
    console: bool = True,
    file_level: str = "DEBUG",
) -> Path:
    """Configure structlog + stdlib logging bridge.

    Console output is human-readable and filtered by ``log_level``. File output
    is JSONL and filtered independently by ``file_level``.
    """
    console_level = _coerce_level(log_level)
    json_level = _coerce_level(file_level)

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"app-{datetime.now().strftime('%Y%m%d')}.jsonl"

    root_logger = logging.getLogger()
    for handler in _managed_handlers(root_logger):
        root_logger.removeHandler(handler)
        try:
            handler.flush()
            handler.close()
        except OSError:
            pass

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    formatter_pre_chain = cast(Any, list(shared_processors))
    handlers: list[logging.Handler] = []

    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(colors=False),
                foreign_pre_chain=formatter_pre_chain,
            )
        )
        setattr(console_handler, _MANAGED_HANDLER_ATTR, True)
        handlers.append(console_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(json_level)
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(ensure_ascii=False),
            foreign_pre_chain=formatter_pre_chain,
        )
    )
    setattr(file_handler, _MANAGED_HANDLER_ATTR, True)
    handlers.append(file_handler)

    for handler in handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(min([handler.level for handler in handlers] or [console_level]))

    for logger_name in _THIRD_PARTY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    structlog.configure(
        processors=cast(Any, [
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]),
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )

    return log_file


def flush_logging_handlers(*, close: bool = False) -> None:
    """Flush, and optionally close, Songyan-managed logging handlers."""
    root_logger = logging.getLogger()
    for handler in list(_managed_handlers(root_logger)):
        try:
            handler.flush()
        except OSError:
            pass
        if close:
            root_logger.removeHandler(handler)
            try:
                handler.close()
            except OSError:
                pass

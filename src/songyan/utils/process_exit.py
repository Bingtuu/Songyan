"""Controlled process-exit helpers for unattended harnesses."""

from __future__ import annotations

import os
from collections.abc import Callable

import structlog

from songyan.config import settings
from songyan.utils.logging_setup import flush_logging_handlers

logger = structlog.get_logger(__name__)


def force_exit_after_run_if_requested(
    *,
    enabled: bool | None = None,
    exit_code: int = 0,
    exit_func: Callable[[int], object] = os._exit,
) -> bool:
    """Invoke ``os._exit`` after explicit caller-side persistence is complete.

    The helper is intentionally small: callers must only invoke it at the
    outermost CLI/harness layer after DB writes, reports, and logs are complete.
    """
    should_exit = settings.force_exit_after_run if enabled is None else enabled
    if not should_exit:
        return False

    logger.warning("force_exit.invoked", exit_code=exit_code)
    flush_logging_handlers(close=True)
    exit_func(exit_code)
    return True

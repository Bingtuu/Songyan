"""Run id validation helpers."""

from __future__ import annotations

import re

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def validate_run_id(run_id: str) -> str:
    """Return a path-safe run id or raise ``ValueError``."""
    if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError(
            "invalid run_id: use 1-128 characters from A-Z, a-z, 0-9, '_', '.', '-' "
            "and start with a letter or digit"
        )
    return run_id

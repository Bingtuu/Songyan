"""Loader helpers for V12 supervision specs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from songyan.exceptions import SongyanError
from songyan.models.supervision import SupervisionSpec

DEFAULT_SUPERVISION_SPEC_PATH = Path("planning") / "supervision_spec.json"


class SupervisionSpecError(SongyanError):
    """Supervision spec file is missing, malformed, or invalid."""


def load_supervision_spec_data(data: dict[str, Any]) -> SupervisionSpec:
    """Validate a raw supervision spec mapping."""
    try:
        return SupervisionSpec.model_validate(data)
    except ValidationError as exc:
        msg = f"supervision spec validation failed: {exc}"
        raise SupervisionSpecError(msg) from exc


def load_supervision_spec_file(path: str | Path) -> SupervisionSpec:
    """Load and validate a supervision spec JSON file."""
    spec_path = Path(path)
    try:
        raw = json.loads(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        msg = f"supervision spec file does not exist: {spec_path}"
        raise SupervisionSpecError(msg) from exc
    except json.JSONDecodeError as exc:
        msg = f"supervision spec file is not valid JSON: {exc}"
        raise SupervisionSpecError(msg) from exc

    if not isinstance(raw, dict):
        msg = "supervision spec top-level value must be a JSON object"
        raise SupervisionSpecError(msg)
    return load_supervision_spec_data(raw)


def load_project_supervision_spec(
    project_root: str | Path,
    relative_path: str | Path = DEFAULT_SUPERVISION_SPEC_PATH,
) -> SupervisionSpec:
    """Load a project-local supervision spec.

    The default project asset path is ``planning/supervision_spec.json``.
    """
    return load_supervision_spec_file(Path(project_root) / Path(relative_path))


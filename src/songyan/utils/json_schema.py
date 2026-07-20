"""JSON Schema validation helpers for packaged resources."""

from __future__ import annotations

import json
from collections.abc import Sequence
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError, ValidationError


class JsonSchemaResourceError(ValueError):
    """Raised when a packaged JSON resource fails schema validation."""


def load_schema(schema_path: Traversable | Path) -> dict[str, Any]:
    """Load and validate a draft-07 JSON Schema from a traversable resource."""
    try:
        with schema_path.open(encoding="utf-8") as f:
            raw_schema = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"Failed to load JSON Schema '{schema_path}': {exc}"
        raise JsonSchemaResourceError(msg) from exc

    if not isinstance(raw_schema, dict):
        msg = f"JSON Schema '{schema_path}' must be an object"
        raise JsonSchemaResourceError(msg)

    try:
        Draft7Validator.check_schema(raw_schema)
    except SchemaError as exc:
        msg = f"Invalid JSON Schema '{schema_path}': {exc.message}"
        raise JsonSchemaResourceError(msg) from exc

    return raw_schema


def validate_json_data(
    data: Any,
    schema: dict[str, Any],
    *,
    resource_name: str,
) -> None:
    """Validate JSON data and raise a compact field-located error on failure."""
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=_error_sort_key)
    if not errors:
        return

    first = errors[0]
    msg = (
        f"JSON Schema validation failed for {resource_name} "
        f"at {_json_pointer(first.path)}: {first.message}"
    )
    raise JsonSchemaResourceError(msg)


def _error_sort_key(error: ValidationError) -> tuple[str, str]:
    return (_json_pointer(error.path), error.message)


def _json_pointer(path: Sequence[str | int]) -> str:
    parts = list(path)
    if not parts:
        return "$"
    rendered = "$"
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered += "." + part
    return rendered

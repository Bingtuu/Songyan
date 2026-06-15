"""Tests for workflows/_helpers.py — DB access compliance (Task 055)."""

from __future__ import annotations

import ast
from pathlib import Path


def test_helpers_no_raw_db_access() -> None:
    """验证 _helpers.py 中不再直接导入或使用 get_db."""
    import songyan.workflows._helpers as helpers_mod

    module_file = Path(helpers_mod.__file__)
    source = module_file.read_text(encoding="utf-8")

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "connection" in module:
                names = [alias.name for alias in node.names]
                assert (
                    "get_db" not in names
                ), f"get_db still imported from {module} in _helpers.py"

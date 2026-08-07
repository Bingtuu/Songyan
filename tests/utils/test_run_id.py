"""Run id validation tests."""

from __future__ import annotations

import pytest

from songyan.utils.run_id import validate_run_id


def test_validate_run_id_accepts_generated_shape() -> None:
    assert validate_run_id("run-abc123") == "run-abc123"
    assert validate_run_id("cli_run.bundle-01") == "cli_run.bundle-01"


@pytest.mark.parametrize(
    "run_id",
    [
        "",
        ".",
        "../outside",
        r"..\outside",
        "/tmp/run",
        r"C:\tmp\run",
        " run-1",
        "-run-1",
    ],
)
def test_validate_run_id_rejects_path_like_values(run_id: str) -> None:
    with pytest.raises(ValueError, match="invalid run_id"):
        validate_run_id(run_id)

"""Tests for V9 Task 184 resource JSON Schema validation."""

from __future__ import annotations

import json
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

import pytest

from songyan.creative_modes.registry import (
    _DEFAULT_MODES_DIR,
    CreativeModeProfileError,
    list_creative_mode_profiles,
    load_creative_mode_profile,
    set_modes_dir,
)
from songyan.creative_modes.registry import (
    clear_cache as clear_mode_cache,
)
from songyan.genres.loader import (
    _DEFAULT_GENRES_DIR,
    GenreProfileError,
    list_genre_profiles,
    load_genre_profile,
    set_genres_dir,
)
from songyan.genres.loader import (
    clear_cache as clear_genre_cache,
)


@pytest.fixture(autouse=True)
def _reset_resource_dirs() -> None:
    try:
        clear_genre_cache()
        clear_mode_cache()
        set_genres_dir(_DEFAULT_GENRES_DIR)
        set_modes_dir(_DEFAULT_MODES_DIR)
        yield
    finally:
        set_genres_dir(_DEFAULT_GENRES_DIR)
        set_modes_dir(_DEFAULT_MODES_DIR)
        clear_genre_cache()
        clear_mode_cache()


def test_schema_files_are_packaged_resources() -> None:
    assert (files("songyan.genres") / "data" / "_schema.json").is_file()
    assert (files("songyan.creative_modes") / "data" / "_schema.json").is_file()


def test_business_resource_lists_exclude_schema_metadata() -> None:
    assert list_genre_profiles() == [
        "mystery_noir",
        "post_apocalyptic",
        "scifi",
        "urban",
        "urban_fantasy",
        "wuxia",
        "xuanhuan",
    ]
    assert list_creative_mode_profiles() == [
        "hybrid",
        "literary",
        "webnovel",
        "webnovel_intense",
    ]


def test_all_packaged_genres_pass_json_schema() -> None:
    for genre_id in list_genre_profiles():
        assert load_genre_profile(genre_id).id == genre_id


def test_all_packaged_modes_pass_json_schema() -> None:
    for mode_id in list_creative_mode_profiles():
        assert load_creative_mode_profile(mode_id).id == mode_id


def test_genre_schema_rejects_unknown_field(tmp_path: Path) -> None:
    data = _load_default_json(_DEFAULT_GENRES_DIR / "scifi.json")
    data["unexpected_typo"] = True
    _write_json(tmp_path / "genres" / "bad.json", data)
    set_genres_dir(tmp_path / "genres")

    with pytest.raises(GenreProfileError) as exc_info:
        load_genre_profile("bad")

    message = str(exc_info.value)
    assert "JSON Schema validation failed" in message
    assert "unexpected_typo" in message


def test_genre_schema_rejects_wrong_nested_type(tmp_path: Path) -> None:
    data = _load_default_json(_DEFAULT_GENRES_DIR / "scifi.json")
    data["style_baseline"]["description_density"] = "dense"
    _write_json(tmp_path / "genres" / "bad.json", data)
    set_genres_dir(tmp_path / "genres")

    with pytest.raises(GenreProfileError) as exc_info:
        load_genre_profile("bad")

    message = str(exc_info.value)
    assert "$.style_baseline.description_density" in message
    assert "not of type" in message


def test_genre_schema_keeps_model_defaults_for_pacing_template(tmp_path: Path) -> None:
    data = {
        "id": "minimal",
        "name": "Minimal",
        "pacing_templates": [
            {
                "emotion_arc": "slow burn",
                "punch_density": 0.5,
                "info_release_strategy": "quiet",
            }
        ],
    }
    _write_json(tmp_path / "genres" / "minimal.json", data)
    set_genres_dir(tmp_path / "genres")

    profile = load_genre_profile("minimal")

    assert profile.pacing_templates[0].chapter_types == []


def test_mode_schema_rejects_invalid_rag_mode(tmp_path: Path) -> None:
    data = _load_default_json(_DEFAULT_MODES_DIR / "webnovel.json")
    data["rag_config"]["enabled"] = "sometimes"
    _write_json(tmp_path / "modes" / "bad.json", data)
    set_modes_dir(tmp_path / "modes")

    with pytest.raises(CreativeModeProfileError) as exc_info:
        load_creative_mode_profile("bad")

    message = str(exc_info.value)
    assert "$.rag_config.enabled" in message
    assert "sometimes" in message


def test_mode_schema_allows_legacy_punch_engine_field() -> None:
    profile = load_creative_mode_profile("webnovel_intense")

    assert profile.id == "webnovel_intense"


def _load_default_json(path: Traversable) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

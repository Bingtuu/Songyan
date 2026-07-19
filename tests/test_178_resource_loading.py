"""Tests for V9 Task 178 resource loading from package data."""

from __future__ import annotations

import json
import shutil
import tomllib
from importlib.resources import files
from pathlib import Path

from evals.runner import resolve_seed_resource
from songyan.creative_modes.registry import (
    _DEFAULT_MODES_DIR,
    list_creative_mode_profiles,
    load_creative_mode_profile,
    set_modes_dir,
)
from songyan.creative_modes.registry import (
    clear_cache as clear_mode_cache,
)
from songyan.genres.loader import (
    _DEFAULT_GENRES_DIR,
    list_genre_profiles,
    load_genre_profile,
    set_genres_dir,
)
from songyan.genres.loader import (
    clear_cache as clear_genre_cache,
)
from songyan.literary_optimization.plugin_loader import (
    load_strategy_plugins,
    reset_plugins_dir,
)
from songyan.project_templates import ProjectTemplateLoader
from songyan.prompts import get_prompt_loader, reset_prompt_loader


def test_package_resource_directories_are_present() -> None:
    genre_files = sorted((files("songyan.genres") / "data").iterdir())
    mode_files = sorted((files("songyan.creative_modes") / "data").iterdir())
    template_dir = files("songyan.project_templates") / "data"
    cards_dir = files("songyan.prompts") / "cards"
    plugins_dir = files("songyan.prompts") / "literary_plugins"
    seeds_dir = files("evals") / "seeds"
    schema_file = files("songyan.db") / "schema.sql"

    assert [path.name for path in genre_files if path.name.endswith(".json")] == [
        "mystery_noir.json",
        "post_apocalyptic.json",
        "scifi.json",
        "urban.json",
        "urban_fantasy.json",
        "wuxia.json",
        "xuanhuan.json",
    ]
    assert [path.name for path in mode_files if path.name.endswith(".json")] == [
        "hybrid.json",
        "literary.json",
        "webnovel.json",
        "webnovel_intense.json",
    ]
    assert (template_dir / "_schema.json").is_file()
    assert (template_dir / "scifi" / "template.yaml").is_file()
    assert (cards_dir / "writer" / "_manifest.yaml").is_file()
    assert sorted(path.name for path in plugins_dir.iterdir() if path.is_dir()) == [
        "ai_tone_blocklist",
        "few_shot_voice_anchor",
        "minimal_voice_anchor",
        "opposing_goal_anchor",
    ]
    assert (seeds_dir / "xuanhuan_webnovel.json").is_file()
    assert (seeds_dir / "chapters" / "xuanhuan_ch1.md").is_file()
    assert schema_file.is_file()


def test_default_loaders_read_packaged_resources() -> None:
    reset_prompt_loader()
    clear_genre_cache()
    clear_mode_cache()
    reset_plugins_dir()

    assert load_genre_profile("scifi").id == "scifi"
    assert load_creative_mode_profile("webnovel").id == "webnovel"
    assert ProjectTemplateLoader().load("scifi").id == "scifi"
    assert get_prompt_loader().load_card("writer").metadata.agent == "writer"
    assert load_strategy_plugins(["minimal_voice_anchor"], "writer")


def test_resource_injection_points_still_accept_external_dirs(tmp_path: Path) -> None:
    try:
        genre_dir = tmp_path / "genres"
        genre_dir.mkdir()
        genre_data = json.loads((_DEFAULT_GENRES_DIR / "scifi.json").read_text(encoding="utf-8"))
        (genre_dir / "scifi.json").write_text(
            json.dumps(genre_data, ensure_ascii=False),
            encoding="utf-8",
        )
        set_genres_dir(genre_dir)
        assert list_genre_profiles() == ["scifi"]
        assert load_genre_profile("scifi").id == "scifi"

        mode_dir = tmp_path / "modes"
        mode_dir.mkdir()
        mode_data = json.loads((_DEFAULT_MODES_DIR / "webnovel.json").read_text(encoding="utf-8"))
        (mode_dir / "webnovel.json").write_text(
            json.dumps(mode_data, ensure_ascii=False),
            encoding="utf-8",
        )
        set_modes_dir(mode_dir)
        assert list_creative_mode_profiles() == ["webnovel"]
        assert load_creative_mode_profile("webnovel").id == "webnovel"
        set_modes_dir(_DEFAULT_MODES_DIR)
        clear_mode_cache()

        reset_prompt_loader()
        cards_dir = tmp_path / "cards"
        shutil.copytree(
            files("songyan.prompts") / "cards" / "goal_planner",
            cards_dir / "goal_planner",
        )
        assert get_prompt_loader(cards_dir=cards_dir).load_card("goal_planner")

        template_dir = tmp_path / "templates"
        shutil.copytree(
            files("songyan.project_templates") / "data" / "scifi",
            template_dir / "scifi",
        )
        assert ProjectTemplateLoader(templates_dir=template_dir).load("scifi").id == "scifi"
    finally:
        set_genres_dir(_DEFAULT_GENRES_DIR)
        set_modes_dir(_DEFAULT_MODES_DIR)
        clear_genre_cache()
        clear_mode_cache()
        reset_prompt_loader()


def test_literary_plugin_loader_accepts_external_dir(tmp_path: Path) -> None:
    plugin_file = tmp_path / "test_strategy" / "writer.yaml"
    plugin_file.parent.mkdir()
    plugin_file.write_text("content: external plugin fragment\n", encoding="utf-8")

    assert load_strategy_plugins(
        ["test_strategy"],
        "writer",
        plugins_dir=tmp_path,
    ) == ["external plugin fragment"]


def test_evals_seed_resources_resolve_outside_repo(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    config = resolve_seed_resource("evals/seeds/xuanhuan_webnovel.json")
    chapter = resolve_seed_resource("evals/seeds/chapters/xuanhuan_ch1.md")

    assert '"genre_id": "xuanhuan"' in config.read_text(encoding="utf-8")
    assert len(chapter.read_text(encoding="utf-8")) > 100


def test_pyproject_declares_runtime_package_data() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    package_data = data["tool"]["setuptools"]["package-data"]

    assert "**/*.yaml" in package_data["songyan"]
    assert "**/*.json" in package_data["songyan"]
    assert "**/*.md" in package_data["songyan"]
    assert "**/*.sql" in package_data["songyan"]
    assert "seeds/**/*.json" in package_data["evals"]
    assert "seeds/**/*.md" in package_data["evals"]

"""Tests for ProjectTemplateLoader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from songyan.project_templates.loader import (
    ProjectTemplateError,
    ProjectTemplateLoader,
    ProjectTemplateNotFoundError,
)


@pytest.fixture
def tmp_templates(tmp_path: Path) -> Path:
    base = tmp_path / "project_templates"
    base.mkdir()

    # scifi template
    scifi = base / "scifi"
    scifi.mkdir()
    (scifi / "template.yaml").write_text(
        (
            "id: scifi\n"
            "name: Sci-Fi\n"
            "project_setting:\n"
            "  title: Ark\n"
            "  genre_id: scifi\n"
            "  mode_id: webnovel\n"
            "  protagonist_name: Lin\n"
        ),
        encoding="utf-8",
    )
    (scifi / "outline.json").write_text(
        json.dumps({
            "outline": {"core_conflict": "ark", "mainline_synopsis": "..."},
            "arc_plans": [],
            "plot_threads": [],
        }),
        encoding="utf-8",
    )
    (scifi / "seed.json").write_text(
        json.dumps({"characters": [{"name": "Lin", "role": "protagonist"}]}),
        encoding="utf-8",
    )

    # xuanhuan variant
    xuanhuan = base / "xuanhuan"
    xuanhuan.mkdir()
    (xuanhuan / "template.yaml").write_text(
        (
            "id: xuanhuan\n"
            "name: Xuanhuan\n"
            "project_setting:\n"
            "  title: Ling\n"
            "  genre_id: xuanhuan\n"
            "  mode_id: webnovel_intense\n"
            "  protagonist_name: Lu\n"
        ),
        encoding="utf-8",
    )
    (xuanhuan / "seed.json").write_text(
        json.dumps({"characters": [{"name": "Lu", "role": "protagonist"}]}),
        encoding="utf-8",
    )

    return base


@pytest.fixture
def tmp_seeds(tmp_path: Path) -> Path:
    seeds = tmp_path / "evals" / "seeds"
    seeds.mkdir(parents=True)
    (seeds / "urban_legacy.json").write_text(
        json.dumps({
            "project_name": "Urban Legacy",
            "genre_id": "urban",
            "mode_id": "webnovel",
            "description": "city story",
            "characters": [{"name": "Zhang", "role": "protagonist"}],
            "initial_settings": [],
        }),
        encoding="utf-8",
    )
    return seeds


def test_load_directory_template(tmp_templates: Path) -> None:
    loader = ProjectTemplateLoader(
        templates_dir=tmp_templates,
        seeds_dir=tmp_templates / "evals" / "seeds",
    )
    template = loader.load("scifi")
    assert template.id == "scifi"
    assert template.has_outline
    assert len(template.seed.characters) == 1


def test_load_seed_compatible(tmp_templates: Path, tmp_seeds: Path) -> None:
    loader = ProjectTemplateLoader(
        templates_dir=tmp_templates,
        seeds_dir=tmp_seeds,
    )
    template = loader.load("urban_legacy")
    assert template.project_setting.genre_id == "urban"
    assert template.project_setting.title == "Urban Legacy"


def test_list_templates(tmp_templates: Path, tmp_seeds: Path) -> None:
    loader = ProjectTemplateLoader(
        templates_dir=tmp_templates,
        seeds_dir=tmp_seeds,
    )
    ids = loader.list_templates()
    assert "scifi" in ids
    assert "urban_legacy" in ids


def test_unknown_template_raises(tmp_templates: Path) -> None:
    loader = ProjectTemplateLoader(
        templates_dir=tmp_templates,
        seeds_dir=tmp_templates / "evals" / "seeds",
    )
    with pytest.raises(ProjectTemplateNotFoundError):
        loader.load("not_exists")


def test_circular_inheritance_raises(tmp_path: Path) -> None:
    base = tmp_path / "project_templates"
    base.mkdir()
    a = base / "a"
    a.mkdir()
    (a / "template.yaml").write_text(
        (
            "id: a\n"
            "extends: b\n"
            "project_setting:\n"
            "  genre_id: scifi\n"
            "  mode_id: webnovel\n"
            "  protagonist_name: A\n"
        ),
        encoding="utf-8",
    )
    b = base / "b"
    b.mkdir()
    (b / "template.yaml").write_text(
        (
            "id: b\n"
            "extends: a\n"
            "project_setting:\n"
            "  genre_id: scifi\n"
            "  mode_id: webnovel\n"
            "  protagonist_name: B\n"
        ),
        encoding="utf-8",
    )
    loader = ProjectTemplateLoader(
        templates_dir=base,
        seeds_dir=base / "evals" / "seeds",
    )
    with pytest.raises(ProjectTemplateError, match="Circular"):
        loader.load("a")

"""Tests for template inheritance and variants."""

from __future__ import annotations

import pytest

from songyan.project_templates.loader import (
    ProjectTemplateError,
    ProjectTemplateLoader,
)


def test_variant_inherits_outline_and_seed(tmp_path_factory) -> None:
    base = tmp_path_factory.mktemp("templates")

    parent = base / "xuanhuan"
    parent.mkdir()
    (parent / "template.yaml").write_text(
        """id: xuanhuan
name: Xuanhuan
project_setting:
  title: Parent
  genre_id: xuanhuan
  mode_id: webnovel
  protagonist_name: Lu
""",
        encoding="utf-8",
    )
    (parent / "seed.json").write_text(
        '{"characters": [{"name": "Lu", "role": "protagonist"}]}',
        encoding="utf-8",
    )

    variant = parent / "cultivation"
    variant.mkdir()
    (variant / "template.yaml").write_text(
        """id: xuanhuan_cultivation
name: Cultivation
extends: xuanhuan
overwrite:
  project_setting:
    title: Child
    protagonist_name: Han
  seed:
    characters:
      - name: Han
        role: protagonist
""",
        encoding="utf-8",
    )

    loader = ProjectTemplateLoader(templates_dir=base, seeds_dir=base / "evals" / "seeds")
    template = loader.load("xuanhuan/cultivation")
    assert template.project_setting.title == "Child"
    assert template.project_setting.protagonist_name == "Han"
    assert template.seed.characters[0].name == "Han"


def test_circular_inheritance_raises(tmp_path_factory) -> None:
    base = tmp_path_factory.mktemp("templates")
    a = base / "a"
    a.mkdir()
    (a / "template.yaml").write_text(
        """id: a
extends: b
project_setting:
  genre_id: scifi
  protagonist_name: A
""",
        encoding="utf-8",
    )
    b = base / "b"
    b.mkdir()
    (b / "template.yaml").write_text(
        """id: b
extends: a
project_setting:
  genre_id: scifi
  protagonist_name: B
""",
        encoding="utf-8",
    )

    loader = ProjectTemplateLoader(templates_dir=base, seeds_dir=base / "evals" / "seeds")
    with pytest.raises(ProjectTemplateError, match="Circular"):
        loader.load("a")

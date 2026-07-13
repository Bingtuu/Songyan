"""Tests for ProjectTemplate models."""

from __future__ import annotations

import pytest

from songyan.models.project import ProjectSetting
from songyan.models.project_template import (
    ProjectTemplate,
    TemplateSeedCharacter,
    TemplateSeedNumericalSystem,
    TemplateSeedSetting,
)


def test_project_template_minimal() -> None:
    project = ProjectSetting(
        title="Test",
        genre_id="scifi",
        mode_id="webnovel",
        protagonist_name="Lin",
    )
    template = ProjectTemplate(id="scifi", name="Sci-Fi", project_setting=project)
    assert template.id == "scifi"
    assert not template.has_outline


def test_template_seed_character_defaults() -> None:
    char = TemplateSeedCharacter(name="Alice")
    assert char.role == "supporting"
    assert char.initial_state == {}


def test_template_seed_setting_requires_key() -> None:
    with pytest.raises(ValueError):
        TemplateSeedSetting(setting_name="X", description="Y")


def test_template_seed_numerical_system() -> None:
    ns = TemplateSeedNumericalSystem(
        name="Cultivation",
        levels=["Qi1", "Qi2"],
        base_unit="spirit",
    )
    assert ns.levels == ["Qi1", "Qi2"]


def test_project_template_set_outline() -> None:
    from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline

    project = ProjectSetting(
        title="Test",
        genre_id="scifi",
        protagonist_name="Lin",
    )
    template = ProjectTemplate(id="scifi", project_setting=project)
    outline = StoryOutline(
        project_id="p1",
        core_conflict="test",
        mainline_synopsis="test",
    )
    arcs = [ArcPlan(
        arc_id="a1",
        project_id="p1",
        arc_index=0,
        start_chapter=1,
        end_chapter=10,
        arc_goal="test",
    )]
    threads = [PlotThread(
        thread_id="t1",
        project_id="p1",
        title="test",
    )]
    template.set_outline(outline, arcs, threads)
    assert template.has_outline
    assert template.outline_tuple == (outline, arcs, threads)

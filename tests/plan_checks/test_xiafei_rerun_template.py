"""The rerun ships the same 霞飞路 template the v4 drive used."""

from __future__ import annotations

from pathlib import Path

from songyan.project_templates.loader import ProjectTemplateLoader

_TEMPLATE_PARENT = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "experiments"
    / "xiafei-plan-gate-rerun-2026-10-25"
    / "tpl"
)


def test_experiment_template_loads() -> None:
    template = ProjectTemplateLoader(templates_dir=_TEMPLATE_PARENT).load("xiafei")

    assert template.project_setting.title == "霞飞路旧案"
    assert template.project_setting.genre_id == "urban"
    assert template.project_setting.protagonist_name == "顾怀瑾"
    assert template.has_outline is True
    assert [row.name for row in template.seed.characters] == ["顾怀瑾"]
    assert any(row.setting_key == "pawnshop" for row in template.seed.initial_settings)

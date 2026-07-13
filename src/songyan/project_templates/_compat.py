"""将旧版 evals/seeds/*.json 转换为 ProjectTemplate."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from songyan.cli.outline_import import load_outline_file
from songyan.models.project import ProjectSetting
from songyan.models.project_template import (
    ProjectTemplate,
    TemplateSeed,
    TemplateSeedCharacter,
    TemplateSeedNumericalSystem,
    TemplateSeedSetting,
)


def seed_to_template(seed_path: Path) -> ProjectTemplate:
    """把单文件种子转换为 ProjectTemplate."""
    data = json.loads(seed_path.read_text(encoding="utf-8"))

    project = ProjectSetting(
        title=data.get("project_name", ""),
        genre_id=data["genre_id"],
        mode_id=data.get("mode_id", "webnovel"),
        protagonist_name=_extract_protagonist_name(data),
        protagonist_background="",
        core_hook=data.get("description", ""),
        target_reader_expectation="",
        target_word_count=100_000,
        tone="",
    )

    seed = TemplateSeed(
        characters=[
            TemplateSeedCharacter(
                name=c["name"],
                role=c.get("role", "supporting"),
                age=c.get("age"),
                description=c.get("description", ""),
                initial_state=c.get("initial_state", {}),
            )
            for c in data.get("characters", [])
        ],
        initial_settings=[
            TemplateSeedSetting(
                setting_key=s["setting_key"],
                setting_name=s["setting_name"],
                description=s["description"],
                source_quote=s.get("source_quote", ""),
            )
            for s in data.get("initial_settings", [])
        ],
        numerical_system=_parse_numerical_system(data.get("numerical_system")),
    )

    template = ProjectTemplate(
        id=seed_path.stem,
        name=seed_path.stem,
        project_setting=project,
        seed=seed,
    )

    # 若种子包含 outline 字段，使用标准 outline 导入
    if "outline" in data:
        with TemporaryDirectory() as tmpdir:
            outline_path = Path(tmpdir) / "outline.json"
            outline_path.write_text(json.dumps(data["outline"]), encoding="utf-8")
            outline, arcs, threads = load_outline_file(str(outline_path), "dummy")
        template.set_outline(outline, arcs, threads)

    return template


def _extract_protagonist_name(data: dict[str, Any]) -> str:
    for c in data.get("characters", []):
        if c.get("role") == "protagonist":
            return str(c["name"])
    if data.get("characters"):
        return str(data["characters"][0]["name"])
    return "主角"


def _parse_numerical_system(
    raw: dict[str, Any] | None,
) -> TemplateSeedNumericalSystem | None:
    if not raw:
        return None
    return TemplateSeedNumericalSystem(
        name=raw.get("name", ""),
        levels=raw.get("levels", []),
        base_unit=raw.get("base_unit", ""),
        formula_hint=raw.get("formula_hint", ""),
    )

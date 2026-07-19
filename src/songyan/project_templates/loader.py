"""ProjectTemplate 加载器."""

from __future__ import annotations

import json
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, cast

import structlog
import yaml

from songyan.cli.outline_import import load_outline_file
from songyan.creative_modes.registry import (
    CreativeModeProfileError,
    load_creative_mode_profile,
)
from songyan.genres.loader import GenreProfileError, load_genre_profile
from songyan.models.project_template import (
    ProjectTemplate,
    TemplateSeed,
)
from songyan.project_templates._compat import seed_to_template

logger = structlog.get_logger(__name__)

_DEFAULT_TEMPLATES_DIR = files("songyan.project_templates") / "data"
_DEFAULT_SEEDS_DIR = files("evals") / "seeds"


class ProjectTemplateError(ValueError):
    """模板加载或校验失败."""


class ProjectTemplateNotFoundError(ProjectTemplateError):
    """模板 ID 不存在."""


class ProjectTemplateLoader:
    """扫描并加载项目模板."""

    def __init__(
        self,
        templates_dir: Traversable | Path | None = None,
        seeds_dir: Traversable | Path | None = None,
    ) -> None:
        self._templates_dir = templates_dir or _DEFAULT_TEMPLATES_DIR
        self._seeds_dir = seeds_dir or _DEFAULT_SEEDS_DIR

    def list_templates(self) -> list[str]:
        """列出可用模板 ID（目录式 + 种子兼容）."""
        ids: set[str] = set()
        if self._templates_dir.exists():
            for p in self._templates_dir.iterdir():
                if p.is_dir() and (p / "template.yaml").exists():
                    ids.add(p.name)
                    # variants
                    for vp in p.iterdir():
                        if vp.is_dir() and (vp / "template.yaml").exists():
                            ids.add(f"{p.name}/{vp.name}")
        if self._seeds_dir.exists():
            for p in self._seeds_dir.iterdir():
                if not p.is_file() or not p.name.endswith(".json"):
                    continue
                try:
                    data = json.loads(p.read_text(encoding="utf-8-sig"))
                except (OSError, json.JSONDecodeError):
                    logger.warning("Skipping unreadable seed file", path=str(p))
                    continue
                if not isinstance(data, dict) or not data.get("genre_id"):
                    logger.warning("Skipping non-seed JSON file", path=str(p))
                    continue
                ids.add(p.name.removesuffix(".json"))
        return sorted(ids)

    def load(self, template_id: str) -> ProjectTemplate:
        """加载指定模板."""
        return self._load(template_id, seen=set())

    def _load(self, template_id: str, seen: set[str]) -> ProjectTemplate:
        if template_id in seen:
            raise ProjectTemplateError(
                f"Circular template inheritance detected: {' -> '.join(seen)} -> {template_id}"
            )
        seen = seen | {template_id}

        # 1. 目录式模板
        template_path = self._templates_dir / template_id / "template.yaml"
        if template_path.exists():
            return self._load_directory_template(template_id, template_path.parent, seen=seen)

        # 2. variants
        if "/" in template_id:
            parent, variant = template_id.split("/", 1)
            variant_path = self._templates_dir / parent / variant / "template.yaml"
            if variant_path.exists():
                return self._load_directory_template(
                    template_id, variant_path.parent, parent_id=parent, seen=seen
                )

        # 3. evals/seeds 兼容
        seed_path = self._seeds_dir / f"{template_id}.json"
        if seed_path.exists():
            template = seed_to_template(seed_path)
            self._validate_genre_mode(template, template_id)
            return template

        available = self.list_templates()
        raise ProjectTemplateNotFoundError(
            f"Template '{template_id}' not found. Available: {available or 'none'}"
        )

    def _load_directory_template(
        self,
        template_id: str,
        source_dir: Traversable | Path,
        parent_id: str | None = None,
        seen: set[str] | None = None,
    ) -> ProjectTemplate:
        seen = seen or set()
        template_file = source_dir / "template.yaml"
        with template_file.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        extends = raw.get("extends")
        if extends is None and parent_id is not None:
            extends = parent_id

        # 继承合并
        base_template: ProjectTemplate | None = None
        if extends:
            base_template = self._load(extends, seen)
            raw = self._merge_overwrite(base_template, raw)

        raw["source_dir"] = source_dir
        template = ProjectTemplate(**raw)

        # 校验 genre / mode 存在
        self._validate_genre_mode(template, template_id)

        # 加载 outline.json
        outline_file = source_dir / "outline.json"
        if outline_file.exists():
            # "dummy" 为占位 project_id；初始化时大纲会重新绑定到真实 project_id
            outline, arcs, threads = load_outline_file(str(outline_file), "dummy")
            template.set_outline(outline, arcs, threads)
        elif base_template and base_template.has_outline:
            outline_tuple = base_template.outline_tuple
            if outline_tuple is None:
                raise ProjectTemplateError(
                    f"Template '{template_id}' inherited outline from base "
                    f"'{base_template.id}' but outline data is missing"
                )
            outline, arcs, threads = outline_tuple
            template.set_outline(outline, arcs, threads)

        # 加载 seed.json（变体目录优先；overwrite/继承合并已在 _merge_overwrite 中完成）
        seed_file = source_dir / "seed.json"
        if seed_file.exists():
            with seed_file.open(encoding="utf-8") as f:
                seed_data = json.load(f)
            template.seed = TemplateSeed(**seed_data)

        return template

    def _validate_genre_mode(
        self, template: ProjectTemplate, template_id: str
    ) -> None:
        """校验模板引用的 genre 与 mode 配置真实存在."""
        try:
            load_genre_profile(template.project_setting.genre_id)
        except GenreProfileError as exc:
            genre_id = template.project_setting.genre_id
            raise ProjectTemplateError(
                f"Template '{template_id}' references unknown genre: {genre_id}"
            ) from exc
        try:
            load_creative_mode_profile(template.project_setting.mode_id)
        except CreativeModeProfileError as exc:
            mode_id = template.project_setting.mode_id
            raise ProjectTemplateError(
                f"Template '{template_id}' references unknown mode: {mode_id}"
            ) from exc

    @staticmethod
    def _merge_overwrite(
        base: ProjectTemplate, child_raw: dict[str, Any]
    ) -> dict[str, Any]:
        """递归合并 overwrite 到父模板 raw dict."""
        merged = base.model_dump(exclude={"id", "name", "extends", "overwrite", "source_dir"})
        overwrite = child_raw.get("overwrite") or {}

        def deep_merge(dst: Any, src: Any) -> Any:
            result: Any
            if isinstance(dst, dict) and isinstance(src, dict):
                result = dict(dst)
                for k, v in src.items():
                    result[k] = deep_merge(result.get(k), v)
                return result
            return src

        merged = cast(dict[str, Any], deep_merge(merged, overwrite))
        # 保留子模板顶层字段；project_setting/seed 等嵌套 dict 需要深度合并
        for key in ("id", "name", "extends"):
            if key in child_raw:
                merged[key] = child_raw[key]
        for key, value in child_raw.items():
            if key in {"id", "name", "extends", "overwrite", "source_dir"}:
                continue
            merged[key] = deep_merge(merged.get(key), value)
        return merged

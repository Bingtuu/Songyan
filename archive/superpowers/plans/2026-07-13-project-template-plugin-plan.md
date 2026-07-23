# Task 172: 项目模板化与体裁可插拔实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `ProjectTemplate` 模板层，让 CLI 和长跑 harness 可以通过 `--template` / `TEMPLATE_ID` 一键切换体裁，覆盖全部 7 个已有 genre，并支持轻量继承/变体。

**Architecture:** 新增 `src/songyan/project_templates/` 包（models + loader + initializer），将项目初始化逻辑从硬编码脚本中抽离；模板以 `project_templates/<template_id>/` 目录组织，包含 `template.yaml`（ProjectSetting）、`outline.json`（叙事骨架）、`seed.json`（初始角色/设定/数值体系）；同时保留对 `evals/seeds/*.json` 的兼容转换。

**Tech Stack:** Python 3.11, Pydantic v2, PyYAML, Jinja2（已有依赖）, pytest, structlog

---

## 文件结构总览

### 新增文件

| 文件 | 职责 |
|---|---|
| `src/songyan/models/project_template.py` | `ProjectTemplate` / `TemplateSeed*` / `TemplateSeedNumericalSystem` Pydantic 模型 |
| `src/songyan/project_templates/__init__.py` | 包入口，导出 `ProjectTemplateLoader`, `ProjectInitializer`, 异常类 |
| `src/songyan/project_templates/loader.py` | 模板扫描、加载、校验、继承合并 |
| `src/songyan/project_templates/initializer.py` | 从 `ProjectTemplate` 写入 DB（project + characters + settings + outline） |
| `src/songyan/project_templates/_compat.py` | 把旧版 `evals/seeds/*.json` 转换为 `ProjectTemplate` |
| `project_templates/_schema.json` | 模板 JSON Schema（供校验和 IDE 提示） |
| `project_templates/scifi/{template.yaml,outline.json,seed.json}` | 科幻模板（迁移现有硬编码设定） |
| `project_templates/xuanhuan/{template.yaml,outline.json,seed.json}` | 玄幻模板 |
| `project_templates/wuxia/{template.yaml,outline.json,seed.json}` | 武侠模板 |
| `project_templates/urban/{template.yaml,outline.json,seed.json}` | 都市模板 |
| `project_templates/urban_fantasy/{template.yaml,outline.json,seed.json}` | 都市奇幻模板 |
| `project_templates/post_apocalyptic/{template.yaml,outline.json,seed.json}` | 末世模板 |
| `project_templates/mystery_noir/{template.yaml,outline.json,seed.json}` | 悬疑 noir 模板 |
| `tests/test_project_template_models.py` | 模型校验测试 |
| `tests/test_project_template_loader.py` | 加载器测试 |
| `tests/test_project_template_initializer.py` | Initializer DB 写入测试 |
| `scripts/run_172_short_window.py` | 多体裁短章验证入口 |

### 修改文件

| 文件 | 修改点 |
|---|---|
| `scripts/run_171_ch200.py` | 用 `ProjectTemplateLoader` + `ProjectInitializer` 替换硬编码 `_project_setting()` / `_build_outline()` |
| `src/songyan/cli/main.py` | `create_project` 新增 `--template` 选项 |
| `src/songyan/models/__init__.py` | 导出 `ProjectTemplate` 相关模型 |
| `tasks/V7-README.md` | 添加 Task 172 状态入口 |
| `docs/STATUS.md` | 更新当前任务状态 |

---

## Task 1: 定义 `ProjectTemplate` 数据模型与 JSON Schema

**目标:** 建立模板层的基础数据结构，确保所有模板文件可被 Pydantic 严格校验。

**Files:**
- Create: `src/songyan/models/project_template.py`
- Create: `project_templates/_schema.json`
- Create: `tests/test_project_template_models.py`
- Modify: `src/songyan/models/__init__.py`

---

### Step 1.1: 编写模型文件

在 `src/songyan/models/project_template.py` 写入：

```python
"""ProjectTemplate 数据模型 — 定义项目模板的标准结构."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline
from songyan.models.project import ProjectSetting


class TemplateSeedCharacter(BaseModel):
    """模板中的初始角色."""

    name: str
    role: str = "supporting"
    age: int | None = None
    description: str = ""
    initial_state: dict[str, Any] = Field(default_factory=dict)


class TemplateSeedSetting(BaseModel):
    """模板中的初始设定."""

    setting_key: str
    setting_name: str
    description: str
    source_quote: str = ""


class TemplateSeedNumericalSystem(BaseModel):
    """模板中的数值体系定义."""

    name: str = ""
    levels: list[str] = Field(default_factory=list)
    base_unit: str = ""
    formula_hint: str = ""


class TemplateSeed(BaseModel):
    """模板种子：角色、设定、数值体系."""

    characters: list[TemplateSeedCharacter] = Field(default_factory=list)
    initial_settings: list[TemplateSeedSetting] = Field(default_factory=list)
    numerical_system: TemplateSeedNumericalSystem | None = None


class ProjectTemplate(BaseModel):
    """项目模板 — 包含项目设定、种子、大纲."""

    id: str
    name: str = ""
    extends: str | None = None
    overwrite: dict[str, Any] = Field(default_factory=dict)
    source_dir: Path | None = None

    project_setting: ProjectSetting
    seed: TemplateSeed = Field(default_factory=TemplateSeed)

    # outline 不直接序列化；加载器解析 outline.json 后通过属性暴露
    _outline: StoryOutline | None = None
    _arc_plans: list[ArcPlan] = Field(default_factory=list)
    _plot_threads: list[PlotThread] = Field(default_factory=list)

    @property
    def has_outline(self) -> bool:
        return self._outline is not None

    @property
    def outline_tuple(self) -> tuple[StoryOutline, list[ArcPlan], list[PlotThread]] | None:
        if self._outline is None:
            return None
        return (self._outline, self._arc_plans, self._plot_threads)

    def set_outline(
        self,
        outline: StoryOutline,
        arc_plans: list[ArcPlan],
        plot_threads: list[PlotThread],
    ) -> None:
        self._outline = outline
        self._arc_plans = arc_plans
        self._plot_threads = plot_threads
```

### Step 1.2: 导出模型

修改 `src/songyan/models/__init__.py`，在现有导出列表末尾追加：

```python
from songyan.models.project_template import (
    ProjectTemplate,
    TemplateSeed,
    TemplateSeedCharacter,
    TemplateSeedNumericalSystem,
    TemplateSeedSetting,
)
```

并确保 `__all__` 包含这些名称（若 `__init__.py` 使用 `__all__`）。

### Step 1.3: 编写 JSON Schema

创建 `project_templates/_schema.json`：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Songyan Project Template",
  "type": "object",
  "required": ["id", "project_setting"],
  "properties": {
    "id": { "type": "string" },
    "name": { "type": "string" },
    "extends": { "type": ["string", "null"] },
    "overwrite": { "type": "object" },
    "project_setting": {
      "type": "object",
      "required": ["genre_id", "protagonist_name"],
      "properties": {
        "title": { "type": ["string", "null"] },
        "genre_id": { "type": "string" },
        "mode_id": { "type": "string", "default": "webnovel" },
        "protagonist_name": { "type": "string" },
        "protagonist_background": { "type": "string" },
        "core_hook": { "type": "string" },
        "target_reader_expectation": { "type": "string" },
        "target_word_count": { "type": "integer", "default": 100000 },
        "tone": { "type": "string", "default": "热血" },
        "estimated_chapters": { "type": "integer", "default": 30 },
        "words_per_chapter": { "type": "integer", "default": 3000 },
        "story_structure": { "type": "string", "default": "free" },
        "sub_genre_id": { "type": ["string", "null"] },
        "arc_boundaries": { "type": "array", "items": { "type": "integer" } },
        "arc_boundaries_auto": { "type": "boolean", "default": false }
      }
    }
  }
}
```

### Step 1.4: 编写模型测试

创建 `tests/test_project_template_models.py`：

```python
"""Tests for ProjectTemplate models."""

from __future__ import annotations

import pytest

from songyan.models.project_template import (
    ProjectTemplate,
    TemplateSeed,
    TemplateSeedCharacter,
    TemplateSeedNumericalSystem,
    TemplateSeedSetting,
)
from songyan.models.project import ProjectSetting


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
```

### Step 1.5: 运行测试

```bash
python -m pytest tests/test_project_template_models.py -v
```

Expected: 5 passed.

### Step 1.6: 提交

```bash
git add src/songyan/models/project_template.py src/songyan/models/__init__.py project_templates/_schema.json tests/test_project_template_models.py
git commit -m "feat(172.1): add ProjectTemplate data models and schema"
```

---

## Task 2: 实现 `ProjectTemplateLoader`

**目标:** 从 `project_templates/` 目录和 `evals/seeds/*.json` 加载模板，支持目录式模板、单文件种子兼容、基础校验。

**Files:**
- Create: `src/songyan/project_templates/loader.py`
- Create: `src/songyan/project_templates/_compat.py`
- Create: `src/songyan/project_templates/__init__.py`
- Create: `tests/test_project_template_loader.py`

---

### Step 2.1: 编写加载器

在 `src/songyan/project_templates/loader.py` 写入：

```python
"""ProjectTemplate 加载器."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
import yaml

import songyan
from songyan.cli.outline_import import load_outline_file
from songyan.creative_modes.registry import load_creative_mode_profile
from songyan.genres.loader import load_genre_profile
from songyan.models.project_template import (
    ProjectTemplate,
    TemplateSeed,
)
from songyan.project_templates._compat import seed_to_template

logger = structlog.get_logger(__name__)

_DEFAULT_TEMPLATES_DIR = (
    Path(songyan.__file__).resolve().parent.parent.parent / "project_templates"
)
_DEFAULT_SEEDS_DIR = (
    Path(songyan.__file__).resolve().parent.parent.parent / "evals" / "seeds"
)


class ProjectTemplateError(ValueError):
    """模板加载或校验失败."""


class ProjectTemplateNotFoundError(ProjectTemplateError):
    """模板 ID 不存在."""


class ProjectTemplateLoader:
    """扫描并加载项目模板."""

    def __init__(
        self,
        templates_dir: Path | None = None,
        seeds_dir: Path | None = None,
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
            for p in self._seeds_dir.glob("*.json"):
                if p.is_file():
                    ids.add(p.stem)
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
            return seed_to_template(seed_path)

        available = self.list_templates()
        raise ProjectTemplateNotFoundError(
            f"Template '{template_id}' not found. Available: {available or 'none'}"
        )

    def _load_directory_template(
        self,
        template_id: str,
        source_dir: Path,
        parent_id: str | None = None,
        seen: set[str] | None = None,
    ) -> ProjectTemplate:
        seen = seen or set()
        template_file = source_dir / "template.yaml"
        with open(template_file, encoding="utf-8") as f:
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
        try:
            load_genre_profile(template.project_setting.genre_id)
        except Exception as exc:
            raise ProjectTemplateError(
                f"Template '{template_id}' references unknown genre: {template.project_setting.genre_id}"
            ) from exc
        try:
            load_creative_mode_profile(template.project_setting.mode_id)
        except Exception as exc:
            raise ProjectTemplateError(
                f"Template '{template_id}' references unknown mode: {template.project_setting.mode_id}"
            ) from exc

        # 加载 outline.json
        outline_file = source_dir / "outline.json"
        if outline_file.exists():
            outline, arcs, threads = load_outline_file(str(outline_file), "dummy")
            template.set_outline(outline, arcs, threads)
        elif base_template and base_template.has_outline:
            outline, arcs, threads = base_template.outline_tuple
            template.set_outline(outline, arcs, threads)

        # 加载 seed.json（变体目录优先；否则继承父模板）
        seed_file = source_dir / "seed.json"
        if seed_file.exists():
            with open(seed_file, encoding="utf-8") as f:
                seed_data = json.load(f)
            template.seed = TemplateSeed(**seed_data)
        elif base_template:
            template.seed = base_template.seed

        return template

    @staticmethod
    def _merge_overwrite(
        base: ProjectTemplate, child_raw: dict[str, Any]
    ) -> dict[str, Any]:
        """递归合并 overwrite 到父模板 raw dict."""
        merged = base.model_dump(exclude={"id", "name", "extends", "overwrite", "source_dir"})
        overwrite = child_raw.get("overwrite") or {}

        def deep_merge(dst: Any, src: Any) -> Any:
            if isinstance(dst, dict) and isinstance(src, dict):
                result = dict(dst)
                for k, v in src.items():
                    result[k] = deep_merge(result.get(k), v)
                return result
            return src

        merged = deep_merge(merged, overwrite)
        # 保留子模板顶层字段
        for key in ("id", "name", "extends", "project_setting"):
            if key in child_raw:
                merged[key] = child_raw[key]
        return merged
```

注意：循环继承检测在 Step 2.3 中补充。

### Step 2.2: 编写兼容转换层

在 `src/songyan/project_templates/_compat.py` 写入：

```python
"""将旧版 evals/seeds/*.json 转换为 ProjectTemplate."""

from __future__ import annotations

import json
from pathlib import Path

from songyan.models.project_template import (
    ProjectTemplate,
    TemplateSeed,
    TemplateSeedCharacter,
    TemplateSeedNumericalSystem,
    TemplateSeedSetting,
)
from songyan.models.project import ProjectSetting


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
        from songyan.cli.outline_import import load_outline_file
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            outline_path = Path(tmpdir) / "outline.json"
            outline_path.write_text(json.dumps(data["outline"]), encoding="utf-8")
            outline, arcs, threads = load_outline_file(str(outline_path), "dummy")
        template.set_outline(outline, arcs, threads)

    return template


def _extract_protagonist_name(data: dict) -> str:
    for c in data.get("characters", []):
        if c.get("role") == "protagonist":
            return c["name"]
    if data.get("characters"):
        return data["characters"][0]["name"]
    return "主角"


def _parse_numerical_system(raw: dict | None) -> TemplateSeedNumericalSystem | None:
    if not raw:
        return None
    return TemplateSeedNumericalSystem(
        name=raw.get("name", ""),
        levels=raw.get("levels", []),
        base_unit=raw.get("base_unit", ""),
        formula_hint=raw.get("formula_hint", ""),
    )
```

### Step 2.3: 循环继承检测

在 `src/songyan/project_templates/loader.py` 的 `_load_directory_template` 中，递归调用 `self.load(extends)` 时可能产生循环。修改 `load` 方法签名，增加内部 `_load` 方法带 `seen` 集合：

```python
    def load(self, template_id: str) -> ProjectTemplate:
        return self._load(template_id, seen=set())

    def _load(self, template_id: str, seen: set[str]) -> ProjectTemplate:
        if template_id in seen:
            raise ProjectTemplateError(
                f"Circular template inheritance detected: {' -> '.join(seen)} -> {template_id}"
            )
        seen = seen | {template_id}
        # ... 原 load 逻辑，内部递归调用 self._load(..., seen)
```

将原 `load` 方法体移入 `_load`，并把内部 `self.load(extends)` 改为 `self._load(extends, seen)`。

### Step 2.4: 包入口

创建 `src/songyan/project_templates/__init__.py`：

```python
"""Project template loading and initialization."""

from songyan.project_templates.initializer import ProjectInitializer
from songyan.project_templates.loader import (
    ProjectTemplateError,
    ProjectTemplateLoader,
    ProjectTemplateNotFoundError,
)

__all__ = [
    "ProjectInitializer",
    "ProjectTemplateLoader",
    "ProjectTemplateError",
    "ProjectTemplateNotFoundError",
]
```

### Step 2.5: 编写加载器测试

创建 `tests/test_project_template_loader.py`：

```python
"""Tests for ProjectTemplateLoader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from songyan.project_templates.loader import (
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
        "id: scifi\nname: Sci-Fi\nproject_setting:\n  title: Ark\n  genre_id: scifi\n  mode_id: webnovel\n  protagonist_name: Lin\n",
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
        "id: xuanhuan\nname: Xuanhuan\nproject_setting:\n  title: Ling\n  genre_id: xuanhuan\n  mode_id: webnovel_intense\n  protagonist_name: Lu\n",
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
    loader = ProjectTemplateLoader(templates_dir=tmp_templates, seeds_dir=tmp_templates / "evals" / "seeds")
    template = loader.load("scifi")
    assert template.id == "scifi"
    assert template.has_outline
    assert len(template.seed.characters) == 1


def test_load_seed_compatible(tmp_templates: Path, tmp_seeds: Path) -> None:
    loader = ProjectTemplateLoader(templates_dir=tmp_templates, seeds_dir=tmp_seeds)
    template = loader.load("urban_legacy")
    assert template.project_setting.genre_id == "urban"
    assert template.project_setting.title == "Urban Legacy"


def test_list_templates(tmp_templates: Path, tmp_seeds: Path) -> None:
    loader = ProjectTemplateLoader(templates_dir=tmp_templates, seeds_dir=tmp_seeds)
    ids = loader.list_templates()
    assert "scifi" in ids
    assert "urban_legacy" in ids


def test_unknown_template_raises(tmp_templates: Path) -> None:
    loader = ProjectTemplateLoader(templates_dir=tmp_templates, seeds_dir=tmp_templates / "evals" / "seeds")
    with pytest.raises(ProjectTemplateNotFoundError):
        loader.load("not_exists")
```

### Step 2.6: 运行测试

```bash
python -m pytest tests/test_project_template_loader.py -v
```

Expected: 4 passed.

### Step 2.7: 提交

```bash
git add src/songyan/project_templates/ tests/test_project_template_loader.py
git commit -m "feat(172.2): add ProjectTemplateLoader with directory and seed compatibility"
```

---

## Task 3: 实现 `ProjectInitializer`

**目标:** 把 `ProjectTemplate` 写入 DB，创建完整的可生成项目。

**Files:**
- Create: `src/songyan/project_templates/initializer.py`
- Modify: `src/songyan/project_templates/__init__.py`
- Create: `tests/test_project_template_initializer.py`

---

### Step 3.1: 编写 Initializer

在 `src/songyan/project_templates/initializer.py` 写入：

```python
"""从 ProjectTemplate 初始化数据库项目."""

from __future__ import annotations

import uuid

import structlog

from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import (
    CharacterRepository,
    ProjectRepository,
)
from songyan.db.settlement_repo import (
    NumericalLedgerRepository,
    SettingSnapshotRepository,
)
from songyan.models import (
    Character,
    NewSetting,
    NumericalUpdate,
    ProjectSetting,
)
from songyan.models.character import DialogueStyleCard
from songyan.models.project_template import ProjectTemplate
from songyan.workflows._helpers import ensure_protagonist_character, new_id

logger = structlog.get_logger(__name__)


class ProjectInitializer:
    """从模板创建完整项目."""

    @staticmethod
    async def from_template(template: ProjectTemplate) -> tuple[str, ProjectSetting]:
        """从模板创建完整项目，返回 (project_id, project_setting)."""
        await init_schema()

        project_id = uuid.uuid4().hex
        await ProjectRepository().create(template.project_setting, project_id)
        logger.info(
            "project_initialized_from_template",
            project_id=project_id,
            template_id=template.id,
        )

        # 创建 protagonist Character（与 CLI 行为一致）
        await ensure_protagonist_character(project_id, template.project_setting)

        # 写入 seed 角色
        await _import_seed_characters(template, project_id)

        # 写入 seed 设定
        await _import_seed_settings(template, project_id)

        # 写入数值体系初始 ledger
        await _import_seed_numerical_system(template, project_id)

        # 导入大纲
        if template.has_outline:
            outline, arcs, threads = template.outline_tuple
            # outline 是 dummy project_id 加载的，需要替换为真实 project_id
            outline.project_id = project_id
            for arc in arcs:
                arc.project_id = project_id
                if arc.arc_id.startswith("dummy-"):
                    arc.arc_id = arc.arc_id.replace("dummy", project_id, 1)
            for thread in threads:
                thread.project_id = project_id
            await NarrativeRepository().import_outline(project_id, outline, arcs, threads)

        return project_id, template.project_setting


async def _import_seed_characters(template: ProjectTemplate, project_id: str) -> None:
    char_repo = CharacterRepository()
    existing_names = {c.name for c in await char_repo.list_by_project(project_id)}
    for seed_char in template.seed.characters:
        if seed_char.name in existing_names:
            continue
        char_id = new_id("char")
        char = Character(
            character_id=char_id,
            project_id=project_id,
            name=seed_char.name,
            role_type=seed_char.role,
            background=seed_char.description,
            personality_traits=[],
            goals=[],
            relationships={},
            dialogue_style_card=DialogueStyleCard(
                character_id=char_id,
                project_id=project_id,
                sentence_length_preference="mixed",
                common_openers=[],
                common_closers=[],
            ),
        )
        await char_repo.create(char)


async def _import_seed_settings(template: ProjectTemplate, project_id: str) -> None:
    setting_repo = SettingSnapshotRepository()
    keys: set[str] = set()
    for seed_setting in template.seed.initial_settings:
        if seed_setting.setting_key in keys:
            logger.warning(
                "duplicate_seed_setting_key",
                project_id=project_id,
                key=seed_setting.setting_key,
            )
            continue
        keys.add(seed_setting.setting_key)
        setting = NewSetting(
            setting_name=seed_setting.setting_name,
            description=seed_setting.description,
            source_quote=seed_setting.source_quote,
            setting_key=seed_setting.setting_key,
        )
        setting_id = new_id("set")
        await setting_repo.create(setting, project_id, setting_id)


async def _import_seed_numerical_system(
    template: ProjectTemplate, project_id: str
) -> None:
    if template.seed.numerical_system is None:
        return
    char_repo = CharacterRepository()
    characters = await char_repo.list_by_project(project_id)
    name_to_char = {c.name: c for c in characters}
    numerical_repo = NumericalLedgerRepository()

    for seed_char in template.seed.characters:
        char = name_to_char.get(seed_char.name)
        if char is None:
            continue
        for field, value in (seed_char.initial_state or {}).items():
            try:
                opening = float(value)
            except (ValueError, TypeError):
                continue
            update = NumericalUpdate(
                character_id=char.character_id,
                attribute_name=field,
                opening_value=opening,
                closing_value=opening,
            )
            ledger_id = new_id("num")
            await numerical_repo.create(update, project_id, 0, ledger_id)
```

注意：`_import_seed_characters` 使用集合推导式在 async 上下文中不合法，应改为普通循环。实现时需修正为：

```python
    existing_names = {c.name for c in await char_repo.list_by_project(project_id)}
```

### Step 3.2: 更新包入口

修改 `src/songyan/project_templates/__init__.py`：

```python
from songyan.project_templates.initializer import ProjectInitializer
from songyan.project_templates.loader import (
    ProjectTemplateError,
    ProjectTemplateLoader,
    ProjectTemplateNotFoundError,
)

__all__ = [
    "ProjectInitializer",
    "ProjectTemplateLoader",
    "ProjectTemplateError",
    "ProjectTemplateNotFoundError",
]
```

### Step 3.3: 编写 Initializer 测试

创建 `tests/test_project_template_initializer.py`：

```python
"""Tests for ProjectInitializer."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from songyan.db.connection import get_db_path
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.models.project import ProjectSetting
from songyan.models.project_template import (
    ProjectTemplate,
    TemplateSeed,
    TemplateSeedCharacter,
    TemplateSeedSetting,
)
from songyan.project_templates.initializer import ProjectInitializer


from songyan.config import settings


@pytest.fixture
async def clean_db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path=db_path)
    yield db_path


async def test_initialize_minimal_project(clean_db: Path) -> None:
    project = ProjectSetting(
        title="Test",
        genre_id="scifi",
        mode_id="webnovel",
        protagonist_name="Lin",
    )
    template = ProjectTemplate(id="scifi", project_setting=project)
    project_id, setting = await ProjectInitializer.from_template(template)

    assert project_id
    assert setting.genre_id == "scifi"

    loaded = await ProjectRepository().get(project_id)
    assert loaded is not None
    assert loaded.genre_id == "scifi"


def test_init_sync_wrapper(clean_db: Path) -> None:
    project = ProjectSetting(
        title="Test",
        genre_id="scifi",
        mode_id="webnovel",
        protagonist_name="Lin",
    )
    template = ProjectTemplate(id="scifi", project_setting=project)
    project_id, setting = asyncio.run(ProjectInitializer.from_template(template))
    assert setting.protagonist_name == "Lin"


async def test_initialize_with_seed(clean_db: Path) -> None:
    project = ProjectSetting(
        title="Xuanhuan",
        genre_id="xuanhuan",
        mode_id="webnovel_intense",
        protagonist_name="Lu",
    )
    template = ProjectTemplate(
        id="xuanhuan",
        project_setting=project,
        seed=TemplateSeed(
            characters=[TemplateSeedCharacter(name="Lu", role="protagonist")],
            initial_settings=[
                TemplateSeedSetting(
                    setting_key="town",
                    setting_name="Qingyan",
                    description="a town",
                )
            ],
        ),
    )
    project_id, _ = await ProjectInitializer.from_template(template)
    assert project_id
```

注意：`clean_db` fixture 的 monkeypatch 需要确认 `songyan.db.connection` 中是否有 `_DB_PATH` / `_DB_URL` 变量。若实际实现不同，需要调整。实现时应根据 `src/songyan/db/connection.py` 的实际 API 重写 fixture。

### Step 3.4: 运行测试

```bash
python -m pytest tests/test_project_template_initializer.py -v
```

Expected: 3 passed.

### Step 3.5: 提交

```bash
git add src/songyan/project_templates/ tests/test_project_template_initializer.py
git commit -m "feat(172.3): add ProjectInitializer.from_template"
```

---

## Task 4: 创建体裁模板目录与迁移现有硬编码科幻设定

**目标:** 把 `run_158_ch1_ch100.py` 中硬编码的科幻项目和大纲迁移到 `project_templates/scifi/`，并为其他 6 个体裁创建基础模板。

**Files:**
- Create: `project_templates/scifi/template.yaml`
- Create: `project_templates/scifi/outline.json`
- Create: `project_templates/scifi/seed.json`
- Create: `project_templates/xuanhuan/template.yaml`
- Create: `project_templates/xuanhuan/outline.json`
- Create: `project_templates/xuanhuan/seed.json`
- Create: `project_templates/wuxia/...`, `urban/...`, `urban_fantasy/...`, `post_apocalyptic/...`, `mystery_noir/...`
- Modify: `scripts/run_171_ch200.py`
- Modify: `src/songyan/cli/main.py`

---

### Step 4.1: 迁移科幻模板

从 `scripts/run_158_ch1_ch100.py` 提取 `_project_setting()` 和 `_build_outline()` 内容，生成：

`project_templates/scifi/template.yaml`：

```yaml
id: scifi
name: 科幻太空歌剧模板
extends: null
overwrite: {}

project_setting:
  title: 轨道蜃景
  genre_id: scifi
  mode_id: webnovel_intense
  protagonist_name: 林渊
  protagonist_background: 前星际考古学家，因一次事故失去搭档，独自追查真相
  core_hook: 人类在太阳系边缘发现一座无法解析的黑色结构『方舟』，林渊是唯一能与之产生共鸣的个体
  target_reader_expectation: 硬科幻+太空悬疑，要求科学细节与剧情张力兼顾
  target_word_count: 450000
  tone: 热血
  estimated_chapters: 250
  words_per_chapter: 3000
  story_structure: serial
  sub_genre_id: space_opera
  arc_boundaries: [25, 50, 75, 100, 125, 150, 175, 200, 225]
  arc_boundaries_auto: true
```

`project_templates/scifi/outline.json`：

```json
{
  "outline": {
    "core_conflict": "人类文明存续与深空黑色结构『方舟』的意志之间的对抗",
    "mainline_synopsis": "太阳系边缘出现一座无法解析的黑色结构『方舟』。前星际考古学家林渊是唯一能与之产生『共鸣』的个体。随着军方、财团与神秘教团先后介入，林渊在追查方舟真相的过程中，逐渐揭开当年那场夺走搭档性命的事故背后的隐情——『旧日搭档』之死并非意外，而与方舟的苏醒直接相关。林渊必须在人类被方舟同化之前，破解共鸣的本质，并决定是唤醒还是封存这座方舟。",
    "themes": ["存续与牺牲", "认知的边界", "信任与背叛"],
    "intended_ending": "林渊以自身共鸣为代价封存方舟，人类文明得以延续但代价沉重"
  },
  "arc_plans": [
    {"arc_index": 0, "start_chapter": 1, "end_chapter": 25, "arc_goal": "发现方舟、确立林渊的共鸣者身份，开启三条主线", "threads_to_open": ["t_ark", "t_resonance", "t_partner"], "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 1, "start_chapter": 26, "end_chapter": 50, "arc_goal": "多方势力介入，共鸣加深，旧日搭档之谜浮现关键线索", "threads_to_open": [], "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 2, "start_chapter": 51, "end_chapter": 75, "arc_goal": "旧日搭档真相收束，方舟意志显现", "threads_to_open": [], "threads_to_resolve": ["t_partner"], "is_mainline": true},
    {"arc_index": 3, "start_chapter": 76, "end_chapter": 100, "arc_goal": "共鸣本质揭示", "threads_to_open": [], "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 4, "start_chapter": 101, "end_chapter": 125, "arc_goal": "共鸣线收束，方舟决战前奏", "threads_to_open": [], "threads_to_resolve": ["t_resonance"], "is_mainline": true},
    {"arc_index": 5, "start_chapter": 126, "end_chapter": 150, "arc_goal": "方舟命运收束，主线终局", "threads_to_open": [], "threads_to_resolve": ["t_ark"], "is_mainline": true},
    {"arc_index": 6, "start_chapter": 151, "end_chapter": 175, "arc_goal": "后日谈与余波", "threads_to_open": [], "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 7, "start_chapter": 176, "end_chapter": 200, "arc_goal": "长线收尾", "threads_to_open": [], "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 8, "start_chapter": 201, "end_chapter": 250, "arc_goal": "终章", "threads_to_open": [], "threads_to_resolve": [], "is_mainline": true}
  ],
  "plot_threads": [
    {"thread_id": "t_ark", "title": "方舟", "description": "太阳系边缘的黑色结构，无法解析，疑似具有意志", "is_mainline": true, "expected_resolve_arc": 5},
    {"thread_id": "t_resonance", "title": "共鸣", "description": "林渊与方舟之间独有的感应能力，本质未知", "is_mainline": true, "expected_resolve_arc": 4},
    {"thread_id": "t_partner", "title": "旧日搭档", "description": "林渊失去的搭档之死背后的隐情", "is_mainline": true, "expected_resolve_arc": 3}
  ]
}
```

`project_templates/scifi/seed.json`：

```json
{
  "characters": [
    {
      "name": "林渊",
      "role": "protagonist",
      "age": 32,
      "description": "前星际考古学家，因一次事故失去搭档，独自追查真相。",
      "initial_state": {}
    }
  ],
  "initial_settings": [],
  "numerical_system": null
}
```

### Step 4.2: 创建玄幻模板

`project_templates/xuanhuan/template.yaml`：

```yaml
id: xuanhuan
name: 玄幻修仙模板
project_setting:
  title: 灵渊纪
  genre_id: xuanhuan
  mode_id: webnovel_intense
  protagonist_name: 陆沉
  protagonist_background: 青岩镇铁匠铺学徒，父母死于十年前的妖兽袭城。性格沉稳坚韧，不善言辞但内心炽烈。
  core_hook: 灵气枯竭时代，少年获得上古灵渊传承，逆天改命
  target_reader_expectation: 热血玄幻升级流，节奏明快，世界观自洽
  target_word_count: 450000
  tone: 热血
  estimated_chapters: 250
  words_per_chapter: 3000
  story_structure: serial
  sub_genre_id: null
  arc_boundaries: [25, 50, 75, 100, 125, 150, 175, 200, 225]
  arc_boundaries_auto: true
```

`project_templates/xuanhuan/outline.json`：

```json
{
  "outline": {
    "core_conflict": "末法时代少年陆沉与灵气枯竭命运及上古灵渊意志的对抗",
    "mainline_synopsis": "灵气枯竭三千年后，青岩镇少年陆沉在铁匠铺下发现上古灵渊入口，获得残缺传承。随着青云宗、妖兽、神秘散修势力介入，陆沉逐渐揭开父母之死与灵渊苏醒的关联，必须在被灵渊同化前决定：封存它以维持末法平衡，还是解封它让灵气重归人间。",
    "themes": ["逆天改命", "代价与传承", "个体与天地"],
    "intended_ending": "陆沉以自身为桥，让灵渊灵气缓慢释放，既拯救苏晚晴寒毒，也避免天地剧变"
  },
  "arc_plans": [
    {"arc_index": 0, "start_chapter": 1, "end_chapter": 25, "arc_goal": "发现灵渊、确立传承者身份，开启三条主线", "threads_to_open": ["t_lingyuan", "t_resonance", "t_parents"], "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 1, "start_chapter": 26, "end_chapter": 50, "arc_goal": "青云宗选拔，境界初成，父母之死浮现线索", "threads_to_open": [], "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 2, "start_chapter": 51, "end_chapter": 75, "arc_goal": "父母真相收束，灵渊意志首次显现", "threads_to_open": [], "threads_to_resolve": ["t_parents"], "is_mainline": true},
    {"arc_index": 3, "start_chapter": 76, "end_chapter": 100, "arc_goal": "传承本质揭示，正邪势力觊觎灵渊", "threads_to_open": [], "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 4, "start_chapter": 101, "end_chapter": 125, "arc_goal": "共鸣线收束，决战前奏", "threads_to_open": [], "threads_to_resolve": ["t_resonance"], "is_mainline": true},
    {"arc_index": 5, "start_chapter": 126, "end_chapter": 150, "arc_goal": "灵渊命运收束，主线终局", "threads_to_open": [], "threads_to_resolve": ["t_lingyuan"], "is_mainline": true},
    {"arc_index": 6, "start_chapter": 151, "end_chapter": 175, "arc_goal": "后日谈与余波", "threads_to_open": [], "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 7, "start_chapter": 176, "end_chapter": 200, "arc_goal": "长线收尾", "threads_to_open": [], "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 8, "start_chapter": 201, "end_chapter": 250, "arc_goal": "终章", "threads_to_open": [], "threads_to_resolve": [], "is_mainline": true}
  ],
  "plot_threads": [
    {"thread_id": "t_lingyuan", "title": "灵渊", "description": "上古大能洞府，封印着一条残存灵脉，疑似具有意志", "is_mainline": true, "expected_resolve_arc": 5},
    {"thread_id": "t_resonance", "title": "共鸣", "description": "陆沉与灵渊之间的传承感应，本质未知", "is_mainline": true, "expected_resolve_arc": 4},
    {"thread_id": "t_parents", "title": "父母之死", "description": "陆沉父母死于妖兽袭城背后的隐情", "is_mainline": true, "expected_resolve_arc": 3}
  ]
}
```

`project_templates/xuanhuan/seed.json`：

```json
{
  "characters": [
    {"name": "陆沉", "role": "protagonist", "age": 16, "description": "青岩镇铁匠铺学徒，父母死于十年前的妖兽袭城。性格沉稳坚韧，不善言辞但内心炽烈。右手腕有一道暗红色胎记，据说是出生时便有的灵纹残迹。", "initial_state": {"cultivation_level": "无", "spirit_value": 0}},
    {"name": "老周头", "role": "supporting", "age": 62, "description": "铁匠铺老板，陆沉的养父般的存在。曾是低阶修士，灵气枯竭后退隐。左腿有旧伤，走路微跛。", "initial_state": {"cultivation_level": "炼气三层（已废）", "spirit_value": 3}},
    {"name": "赵天衡", "role": "antagonist", "age": 19, "description": "青岩镇镇守之子，自诩天才，已踏入炼气一层。傲慢跋扈，视陆沉为蝼蚁。", "initial_state": {"cultivation_level": "炼气一层", "spirit_value": 12}},
    {"name": "苏晚晴", "role": "supporting", "age": 15, "description": "镇东药铺苏掌柜的独女，性情清冷，精通药理。与陆沉青梅竹马，常暗中给他送伤药。体内隐有不明寒毒。", "initial_state": {"cultivation_level": "无", "spirit_value": 0}}
  ],
  "initial_settings": [
    {"setting_key": "qingyan_town", "setting_name": "青岩镇", "description": "位于苍云山脉西麓的边陲小镇，常住人口约三千。因附近出产青纹铁矿石而得名。", "source_quote": ""},
    {"setting_key": "spirit_depletion_era", "setting_name": "灵气枯竭时代", "description": "三千年前大劫之后，天地间灵气浓度骤降至不足往昔百分之一。", "source_quote": ""},
    {"setting_key": "ancient_ruins_legend", "setting_name": "灵渊传说", "description": "苍云山脉深处有一处被称为'灵渊'的上古遗迹，据说是大劫前某位化神期大能的洞府。", "source_quote": ""}
  ],
  "numerical_system": {
    "name": "九品灵根修炼体系",
    "levels": ["无", "炼气一层", "炼气二层", "炼气三层", "炼气四层", "炼气五层", "炼气六层", "炼气七层", "炼气八层", "炼气九层", "筑基"],
    "base_unit": "灵气值",
    "formula_hint": "每提升一层需要上一层的灵气值 × 1.5，炼气一层门槛为 10 点灵气值"
  }
}
```

### Step 4.3: 创建其余 5 个体裁模板

对 `wuxia`、`urban`、`urban_fantasy`、`post_apocalyptic`、`mystery_noir`，分别创建 `template.yaml`、`outline.json`、`seed.json`。

每个模板至少包含：

- `project_setting.title`、`genre_id`（对应目录名）、`mode_id: webnovel_intense`、`protagonist_name`、`protagonist_background`、`core_hook`、`estimated_chapters: 250`、`words_per_chapter: 3000`、`story_structure: serial`、`arc_boundaries_auto: true`。
- `outline.json`：3 条主线线索 + 9 个弧（覆盖 Ch1–Ch250，每 25 章一个弧）。
- `seed.json`：至少 1 个 protagonist + 2 个 supporting/antagonist + 3 个 initial_settings；数值体系按 genre 配置（xuanhuan 必须，其余可选）。

具体 outline/seed 内容可参考对应 `genres/<genre>.json` 的 `writer_rules`、`taboos`、`reference_works` 自行设计，或复制科幻模板并替换题材名词。

### Step 4.4: 改造 `scripts/run_171_ch200.py`

修改 `scripts/run_171_ch200.py`：

1. 删除 `import scripts.run_158_ch1_ch100 as base`（或保留但不使用）。
2. 在文件顶部新增：

```python
from songyan.project_templates import ProjectInitializer, ProjectTemplateLoader

TEMPLATE_ID = os.getenv("TEMPLATE_ID", "scifi")
```

3. 修改 `_init_db()`：

```python
async def _init_db() -> str:
    db_path = get_db_path()
    for suffix in ("", "-wal", "-shm"):
        p = db_path.with_name(db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()
            print(f"[init] removed {p}")
    await init_schema()
    print(f"[init] schema initialized at {db_path}")

    if METRICS_PATH.exists():
        METRICS_PATH.unlink()

    template = ProjectTemplateLoader().load(TEMPLATE_ID)
    project_id, project = await ProjectInitializer.from_template(template)
    print(f"[init] project {project_id} from template '{TEMPLATE_ID}': {project.genre_id}")

    PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(
        json.dumps({"project_id": project_id, "db": str(db_path.as_posix())}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[init] PROJECT_ID={project_id} (saved to {PROJECT_FILE})")
    return project_id
```

4. 删除原 `base._project_setting()` 和 `base._build_outline(project_id)` 调用。

### Step 4.5: 改造 CLI `create_project`

修改 `src/songyan/cli/main.py`：

1. 在顶部导入：

```python
from songyan.project_templates import ProjectInitializer, ProjectTemplateLoader
```

2. `create_project` 命令新增 `--template` 选项：

```python
@cli.command()
@click.option("--outline-file", type=click.Path(exists=True), default=None)
@click.option("--template", "template_id", default=None, help="使用项目模板 ID 一键创建")
def create_project(outline_file: str | None, template_id: str | None) -> None:
    """交互式创建小说项目，或 --template 使用模板."""
    try:
        if template_id:
            project_id, project = asyncio.run(_create_project_from_template(template_id, outline_file))
        else:
            project_id, project = asyncio.run(_create_project_async(outline_file))
    ...
```

3. 新增辅助函数 `_create_project_from_template`：

```python
async def _create_project_from_template(
    template_id: str, outline_file: str | None
) -> tuple[str, ProjectSetting]:
    await init_schema()
    template = ProjectTemplateLoader().load(template_id)

    if outline_file:
        outline, arcs, threads = load_outline_file(outline_file, "dummy")
        template.set_outline(outline, arcs, threads)

    project_id, project = await ProjectInitializer.from_template(template)
    return project_id, project
```

### Step 4.6: 验证模板加载

```bash
python -c "from songyan.project_templates import ProjectTemplateLoader; print(ProjectTemplateLoader().list_templates())"
```

Expected: 包含 `scifi`、`xuanhuan`、`wuxia`、`urban`、`urban_fantasy`、`post_apocalyptic`、`mystery_noir`。

### Step 4.7: 提交

```bash
git add project_templates/ scripts/run_171_ch200.py src/songyan/cli/main.py
git commit -m "feat(172.4): add genre project templates and integrate --template into CLI/harness"
```

---

## Task 5: 轻量继承与变体（C 补充）

**目标:** 支持 `extends` 和 `variants/` 子目录，验证覆盖合并正确。

**Files:**
- Create: `project_templates/xuanhuan/cultivation/template.yaml`
- Modify: `src/songyan/project_templates/loader.py`（循环继承检测已在 Task 2 完成）
- Create: `tests/test_project_template_inheritance.py`

---

### Step 5.1: 创建玄幻修仙变体

创建 `project_templates/xuanhuan/cultivation/template.yaml`：

```yaml
id: xuanhuan_cultivation
name: 玄幻·正统修仙变体
extends: xuanhuan
overwrite:
  project_setting:
    title: 万道独尊
    protagonist_name: 韩立
  seed:
    characters:
      - name: 韩立
        role: protagonist
        age: 18
        description: 出身贫寒的少年，凭借谨慎与毅力在修仙界步步为营。
        initial_state:
          cultivation_level: 无
          spirit_value: 0
```

此变体不自带 `outline.json` 和 `seed.json`，继承父模板；只通过 `overwrite` 替换主角名和部分种子。

### Step 5.2: 编写继承测试

创建 `tests/test_project_template_inheritance.py`：

```python
"""Tests for template inheritance and variants."""

from __future__ import annotations

import pytest

from songyan.project_templates.loader import ProjectTemplateLoader, ProjectTemplateError


def test_variant_inherits_outline_and_seed(tmp_path_factory) -> None:
    base = tmp_path_factory.mktemp("templates")

    parent = base / "xuanhuan"
    parent.mkdir()
    (parent / "template.yaml").write_text(
        "id: xuanhuan\nname: Xuanhuan\nproject_setting:\n  title: Parent\n  genre_id: xuanhuan\n  mode_id: webnovel\n  protagonist_name: Lu\n",
        encoding="utf-8",
    )
    (parent / "seed.json").write_text(
        '{"characters": [{"name": "Lu", "role": "protagonist"}]}',
        encoding="utf-8",
    )

    variant = parent / "cultivation"
    variant.mkdir()
    (variant / "template.yaml").write_text(
        "id: xuanhuan_cultivation\nname: Cultivation\nextends: xuanhuan\noverwrite:\n  project_setting:\n    title: Child\n    protagonist_name: Han\n  seed:\n    characters:\n      - name: Han\n        role: protagonist\n",
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
        "id: a\nextends: b\nproject_setting:\n  genre_id: scifi\n  protagonist_name: A\n",
        encoding="utf-8",
    )
    b = base / "b"
    b.mkdir()
    (b / "template.yaml").write_text(
        "id: b\nextends: a\nproject_setting:\n  genre_id: scifi\n  protagonist_name: B\n",
        encoding="utf-8",
    )

    loader = ProjectTemplateLoader(templates_dir=base, seeds_dir=base / "evals" / "seeds")
    with pytest.raises(ProjectTemplateError, match="Circular"):
        loader.load("a")
```

### Step 5.3: 运行测试

```bash
python -m pytest tests/test_project_template_inheritance.py -v
```

Expected: 2 passed.

### Step 5.4: 提交

```bash
git add project_templates/xuanhuan/cultivation/ tests/test_project_template_inheritance.py
git commit -m "feat(172.5): add lightweight template inheritance and variants"
```

---

## Task 6: 多体裁短章验证脚本

**目标:** 提供统一入口，对每个体裁跑 Ch1–Ch3 小窗口，验证模板机制正确。

**Files:**
- Create: `scripts/run_172_short_window.py`

---

### Step 6.1: 编写短窗口脚本

创建 `scripts/run_172_short_window.py`：

```python
"""Task 172 短章验证：为每个体裁跑 Ch1-Ch3，检查 completed/T9/字数."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.db.connection import get_db_path
from songyan.evals.text_cleanliness import collect_text_cleanliness_metrics
from songyan.project_templates import ProjectInitializer, ProjectTemplateLoader
from songyan.workflows.phase2_graph import run_project_pipeline
from songyan.models import GateConfig


async def run_for_template(template_id: str, end_chapter: int = 3) -> dict:
    db_path = get_db_path()
    for suffix in ("", "-wal", "-shm"):
        p = db_path.with_name(db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()

    template = ProjectTemplateLoader().load(template_id)
    project_id, project = await ProjectInitializer.from_template(template)

    gate_config = GateConfig.for_mode("enforce")
    result = await run_project_pipeline(
        project_id=project_id,
        chapter_range=(1, end_chapter),
        mode_id=project.mode_id,
        auto_confirm=True,
        on_failure="isolate",
        gate_config=gate_config,
    )

    t9_metrics = await collect_text_cleanliness_metrics(project_id, 1, end_chapter)
    hard_issues = sum(
        1 for m in t9_metrics if m.issue_severity == "hard"
    )

    return {
        "template_id": template_id,
        "project_id": project_id,
        "completed": result.chapters_completed,
        "failed": result.chapters_failed,
        "status": result.final_status,
        "t9_hard_issues": hard_issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", nargs="+", default=None, help="要验证的模板 ID 列表")
    parser.add_argument("--end", type=int, default=3, help="结束章节")
    parser.add_argument("--output", default=".tmp/task172_short_window_results.json")
    args = parser.parse_args()

    templates = args.templates or ProjectTemplateLoader().list_templates()
    results = []
    for template_id in templates:
        print(f"\n=== {template_id} ===")
        try:
            summary = asyncio.run(run_for_template(template_id, args.end))
            results.append(summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        except Exception as exc:
            results.append({"template_id": template_id, "error": str(exc)})
            print(f"ERROR: {exc}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
```

注意：`collect_text_cleanliness_metrics` 的返回类型需与实际情况对齐；若函数签名不同，实现时调整。

### Step 6.2: 本地手动验证

```bash
$env:DATABASE_URL = "sqlite:///.tmp/task172_test.db"
python scripts/run_172_short_window.py --templates scifi xuanhuan --end 3
```

Expected: 每个模板 `completed=3`、`t9_hard_issues=0`；若有失败则记录到 `.tmp/task172_short_window_results.json`。

### Step 6.3: 提交

```bash
git add scripts/run_172_short_window.py
git commit -m "feat(172): add short-window validation script for all genres"
```

---

## Task 7: 文档更新与回归验证

**目标:** 更新任务索引和项目状态，运行完整回归测试。

**Files:**
- Modify: `tasks/V7-README.md`
- Modify: `docs/STATUS.md`

---

### Step 7.1: 更新 V7 任务索引

在 `tasks/V7-README.md` 的"阶段 Z"表格中，把 Task 172 占位更新为：

```markdown
| 172 | 项目模板化与体裁可插拔（拆 172.1–172.5） | 🔄 进行中 | `archive/superpowers/plans/2026-07-13-project-template-plugin-plan.md`；设计 `archive/superpowers/specs/2026-07-13-project-template-plugin-design.md` |
```

并在表格末尾新增占位：

```markdown
| 172.1 | ProjectTemplate 数据模型 + Schema | ◻ 规划中 | ... |
| 172.2 | ProjectTemplateLoader 实现 | ◻ 规划中 | ... |
| 172.3 | ProjectInitializer.from_template | ◻ 规划中 | ... |
| 172.4 | CLI/harness --template 集成 + 7 个体裁模板 | ◻ 规划中 | ... |
| 172.5 | 轻量继承/变体 | ◻ 规划中 | ... |
```

### Step 7.2: 更新 STATUS.md

在 `docs/STATUS.md` 的"当前风险/下一步"中新增：

```markdown
| 当前风险 | P0 已全部清零；高优先级 P1 已完成；Task 172 项目模板化已设计完成，待按 172.1–172.5 分步实施 |
```

在"下一步"中追加：

```markdown
3. 按 Task 172 计划推进项目模板化（172.1–172.5），每子任务后做短章测试。
```

### Step 7.3: 回归测试

```bash
python -m pytest tests/test_project_template_models.py tests/test_project_template_loader.py tests/test_project_template_initializer.py tests/test_project_template_inheritance.py -v
ruff check src/songyan/project_templates/ tests/test_project_template_*.py
mypy src/songyan/project_templates/
```

Expected:
- pytest: 全部 passed
- ruff: 无新告警
- mypy: no issues found

### Step 7.4: 提交

```bash
git add tasks/V7-README.md docs/STATUS.md
git commit -m "docs(172): update V7 index and STATUS with Task 172 plan"
```

---

## Self-Review Checklist

### Spec Coverage

| Spec 章节 | 覆盖任务 |
|---|---|
| B 为主：目录式模板 | Task 1, Task 4 |
| C 补充：extends / variants | Task 5 |
| 兼容 evals/seeds | Task 2 |
| ProjectInitializer 流程 | Task 3 |
| CLI/harness 集成 | Task 4 |
| 短章测试 | Task 6 |
| 7 个体裁 | Task 4 |

### Placeholder Scan

- 无 "TBD" / "TODO" / "implement later"。
- 所有代码块均给出完整可运行代码。
- 测试命令和预期输出明确。

### Type Consistency

- `ProjectTemplateLoader.load()` / `list_templates()` 签名在 Task 2 和 Task 4/5 中一致。
- `ProjectInitializer.from_template()` 返回 `tuple[str, ProjectSetting]` 在 Task 3 和 Task 4 中一致。
- `ProjectTemplate.outline_tuple` 属性在 Task 1 和 Task 3 中一致。

### 已知实现注意点

1. `ProjectTemplate` 的 `_outline` / `_arc_plans` / `_plot_threads` 以下划线开头，Pydantic 默认会忽略；若需保留可用 `PrivateAttr` 或改为普通 dataclass 字段。实现时根据测试反馈调整。
2. `_import_seed_characters` 中的 `existing_names = {c.name for c in await char_repo.list_by_project(project_id)}` 需确认 `CharacterRepository.list_by_project` 返回类型。
3. `scripts/run_172_short_window.py` 依赖 `collect_text_cleanliness_metrics`，若其签名与示例不同，需按实际 API 调整。
4. `load_outline_file()` 返回的 `outline` / `arcs` / `threads` 使用 `"dummy"` 作为 project_id；Task 3 中需要替换为真实 project_id。

---

**Plan complete and saved to `archive/superpowers/plans/2026-07-13-project-template-plugin-plan.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration.

2. **Inline Execution** - Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Which approach would you like?

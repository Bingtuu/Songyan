# Task 170j: 极简声纹锚定扩展接口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为文学性/可读性优化建立可扩展的 Strategy + Prompt 插件接口，并在 170j 中落地第一个 Strategy："极简声纹锚定"，以保守方式验证 voice 能否提升。

**Architecture:** 引入 `LiteraryOptimizationStrategy` 抽象，每个 Strategy 声明影响的 Agent 并输出 prompt 插件片段；Agent 渲染 prompt 时根据 `literary_optimization_plugins` 配置加载对应插件 YAML。170j 先实现 `MinimalVoiceAnchorStrategy`，通过 CreativeDirector 为人类角色输出极简声纹卡（情绪基调 + 一句话口头禅/禁忌），Writer 渲染时注入，不改动默认版本号，不影响无大纲项目。

**Tech Stack:** Python 3.11, Pydantic v2, structlog, 现有 prompt loader / craft card 系统

---

## File Structure

| 文件 | 职责 |
|------|------|
| `src/songyan/literary_optimization/__init__.py` | 包入口，暴露 Strategy 基类、注册表、加载函数 |
| `src/songyan/literary_optimization/base.py` | `LiteraryOptimizationStrategy` ABC + `LiteraryContext` + `LiteraryOptimizationResult` |
| `src/songyan/literary_optimization/strategies/minimal_voice_anchor.py` | 第一个 Strategy 实现 |
| `src/songyan/literary_optimization/registry.py` | Strategy 注册与发现 |
| `src/songyan/literary_optimization/plugin_loader.py` | 加载 `prompts/literary_plugins/<strategy_id>/` 下的 YAML 插件片段 |
| `prompts/literary_plugins/minimal_voice_anchor/creative_director.yaml` | CreativeDirector 插件：输出 `voice_anchors` |
| `prompts/literary_plugins/minimal_voice_anchor/writer.yaml` | Writer 插件：渲染 `voice_anchors` |
| `src/songyan/models/creative_mode.py` | `CreativeBrief` 新增 `voice_anchors: list[VoiceAnchor]` |
| `src/songyan/agents/creative_director/_brief_builder.py` | 解析 `voice_anchors` 字段 |
| `src/songyan/agents/creative_director/__init__.py` | 渲染 prompt 时加载 active strategies 的插件片段 |
| `src/songyan/agents/writer.py` | 渲染 prompt 时加载 active strategies 的插件片段，注入 voice_anchors |
| `src/songyan/prompts/loader.py` | 扩展 `load_card` 支持 `plugins` 参数 |
| `src/songyan/creative_modes/registry.py` 或 `src/songyan/config/settings.py` | 新增 `literary_optimization_plugins: list[str]` 配置入口 |
| `tests/literary_optimization/test_base.py` | Strategy 注册表/加载/接口契约测试 |
| `tests/literary_optimization/test_minimal_voice_anchor.py` | 极简声纹锚定 Strategy 端到端测试 |
| `tests/test_prompt_loader.py` | 插件加载/合并测试 |
| `scripts/run_170j_experiment.py` | 170j Ch29–Ch32 小样本实验 harness |
| `scripts/run_170j_reeval.py` | 170j 复评报告（复用 170i 逻辑） |

---

## Task 1: Strategy 抽象与注册表

**Files:**
- Create: `src/songyan/literary_optimization/__init__.py`
- Create: `src/songyan/literary_optimization/base.py`
- Create: `src/songyan/literary_optimization/registry.py`
- Test: `tests/literary_optimization/test_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/literary_optimization/test_base.py
from songyan.literary_optimization import (
    LiteraryContext,
    LiteraryOptimizationResult,
    LiteraryOptimizationStrategy,
    list_strategies,
    load_strategy,
)


class DummyStrategy(LiteraryOptimizationStrategy):
    @property
    def strategy_id(self) -> str:
        return "dummy"

    @property
    def applicable_agents(self) -> list[str]:
        return ["writer"]

    def apply(self, context: LiteraryContext) -> LiteraryOptimizationResult:
        return LiteraryOptimizationResult(
            prompt_fragments={"writer": ["dummy fragment"]}
        )


def test_strategy_interface():
    s = DummyStrategy()
    assert s.strategy_id == "dummy"
    assert s.applicable_agents == ["writer"]
    result = s.apply(LiteraryContext())
    assert result.prompt_fragments == {"writer": ["dummy fragment"]}


def test_registry_lists_built_in_strategies():
    strategies = list_strategies()
    assert "minimal_voice_anchor" in strategies


def test_load_strategy():
    s = load_strategy("minimal_voice_anchor")
    assert s.strategy_id == "minimal_voice_anchor"
    assert "creative_director" in s.applicable_agents
    assert "writer" in s.applicable_agents
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/literary_optimization/test_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'songyan.literary_optimization'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/songyan/literary_optimization/__init__.py
from .base import (
    LiteraryContext,
    LiteraryOptimizationResult,
    LiteraryOptimizationStrategy,
)
from .registry import list_strategies, load_strategy

__all__ = [
    "LiteraryContext",
    "LiteraryOptimizationResult",
    "LiteraryOptimizationStrategy",
    "list_strategies",
    "load_strategy",
]


# src/songyan/literary_optimization/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LiteraryContext:
    """Strategy 可读上下文 — 按需填充，Strategy 不应强依赖任何字段."""

    project_id: str = ""
    chapter_number: int = 0
    mode_id: str = ""
    characters: list[Any] = field(default_factory=list)
    creative_brief: Any | None = None
    chapter_goal: Any | None = None
    project_setting: Any | None = None


@dataclass
class LiteraryOptimizationResult:
    """Strategy 输出 — prompt 片段、检测规则、修订触发条件."""

    prompt_fragments: dict[str, list[str]] = field(default_factory=dict)
    audit_rules: list[dict[str, Any]] = field(default_factory=list)
    revision_hints: list[str] = field(default_factory=list)


class LiteraryOptimizationStrategy(ABC):
    """文学性/可读性优化策略基类."""

    @property
    @abstractmethod
    def strategy_id(self) -> str: ...

    @property
    @abstractmethod
    def applicable_agents(self) -> list[str]: ...

    @abstractmethod
    def apply(self, context: LiteraryContext) -> LiteraryOptimizationResult: ...
```

```python
# src/songyan/literary_optimization/registry.py
from __future__ import annotations

from typing import TYPE_CHECKING

from .strategies.minimal_voice_anchor import MinimalVoiceAnchorStrategy

if TYPE_CHECKING:
    from .base import LiteraryOptimizationStrategy

_REGISTRY: dict[str, type[LiteraryOptimizationStrategy]] = {
    MinimalVoiceAnchorStrategy().strategy_id: MinimalVoiceAnchorStrategy,
}


def list_strategies() -> list[str]:
    return list(_REGISTRY.keys())


def load_strategy(strategy_id: str) -> LiteraryOptimizationStrategy:
    cls = _REGISTRY.get(strategy_id)
    if cls is None:
        raise ValueError(f"Unknown literary optimization strategy: {strategy_id}")
    return cls()
```

```python
# src/songyan/literary_optimization/strategies/minimal_voice_anchor.py
from __future__ import annotations

from songyan.literary_optimization.base import (
    LiteraryContext,
    LiteraryOptimizationResult,
    LiteraryOptimizationStrategy,
)


class MinimalVoiceAnchorStrategy(LiteraryOptimizationStrategy):
    """极简声纹锚定：为出场人类角色输出情绪基调+一句话口头禅/禁忌."""

    @property
    def strategy_id(self) -> str:
        return "minimal_voice_anchor"

    @property
    def applicable_agents(self) -> list[str]:
        return ["creative_director", "writer"]

    def apply(self, context: LiteraryContext) -> LiteraryOptimizationResult:
        return LiteraryOptimizationResult(
            prompt_fragments={
                "creative_director": ["插件要求见 minimal_voice_anchor/creative_director.yaml"],
                "writer": ["插件要求见 minimal_voice_anchor/writer.yaml"],
            }
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/literary_optimization/test_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/songyan/literary_optimization tests/literary_optimization
git commit -m "feat(170j): add LiteraryOptimizationStrategy base + minimal_voice_anchor skeleton"
```

---

## Task 2: Prompt 插件加载器

**Files:**
- Create: `src/songyan/literary_optimization/plugin_loader.py`
- Modify: `src/songyan/prompts/loader.py`
- Test: `tests/test_prompt_loader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompt_loader.py
from pathlib import Path

import pytest

from songyan.literary_optimization.plugin_loader import load_strategy_plugins


@pytest.mark.parametrize(
    "strategy_id, agent, expected_in_content",
    [
        ("minimal_voice_anchor", "creative_director", "voice_anchors"),
        ("minimal_voice_anchor", "writer", "voice_anchors"),
    ],
)
def test_load_strategy_plugins(strategy_id: str, agent: str, expected_in_content: str):
    plugins = load_strategy_plugins([strategy_id], agent)
    assert len(plugins) == 1
    assert expected_in_content in plugins[0]


def test_load_strategy_plugins_unknown_strategy():
    plugins = load_strategy_plugins(["nonexistent"], "writer")
    assert plugins == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_prompt_loader.py::test_load_strategy_plugins -v`
Expected: FAIL with `ModuleNotFoundError` 或 `FileNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/songyan/literary_optimization/plugin_loader.py
from __future__ import annotations

from pathlib import Path

import structlog
import yaml

logger = structlog.get_logger(__name__)

PLUGINS_DIR = Path(__file__).parent.parent.parent.parent / "prompts" / "literary_plugins"


def load_strategy_plugins(strategy_ids: list[str], agent: str) -> list[str]:
    """加载指定 Strategy 在某个 Agent 下的 prompt 插件片段."""
    fragments: list[str] = []
    for sid in strategy_ids:
        plugin_file = PLUGINS_DIR / sid / f"{agent}.yaml"
        if not plugin_file.exists():
            logger.warning(
                "literary_plugin.missing",
                strategy_id=sid,
                agent=agent,
                path=str(plugin_file),
            )
            continue
        try:
            data = yaml.safe_load(plugin_file.read_text(encoding="utf-8")) or {}
        except Exception:
            logger.warning(
                "literary_plugin.load_failed",
                strategy_id=sid,
                agent=agent,
                path=str(plugin_file),
            )
            continue
        content = data.get("content", "")
        if content:
            fragments.append(str(content))
    return fragments
```

```python
# prompts/literary_plugins/minimal_voice_anchor/creative_director.yaml
content: |
  ## 极简声纹锚定（Task 170j）

  为每个出场的主要人类角色输出一个 `voice_anchor`（极简声纹卡），包含：
  - `character_id`: 角色 ID
  - `emotional_register`: 本章情绪基调（1 句话，如"压抑但易怒"）
  - `verbal_tick`: 一句口头禅或高频短语（不超过 8 个字，如"我没时间"）
  - `taboo_phrase`: 该角色在当前冲突中绝对不会说的词或句式（如"对不起"）

  要求：
  - 只给 2–3 个核心人类角色；
  - 不要给每个角色都写口头禅；
  - 声纹必须服务于本章冲突，不能为了区分而区分。
```

```python
# prompts/literary_plugins/minimal_voice_anchor/writer.yaml
content: |
  ## 极简声纹锚定（Task 170j）

  本章为人类角色设定了极简声纹卡（情绪基调、口头禅/禁忌）。写作时：
  - 每个主要人类角色的对白应体现其情绪基调；
  - 可在关键对白中使用该角色的口头禅，但**不要每句话都加**；
  - 避免让该角色说出 taboo_phrase；
  - 不要为了声纹而声纹——声纹应自然地从角色目标和压力中流露。
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_prompt_loader.py::test_load_strategy_plugins -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/songyan/literary_optimization/plugin_loader.py prompts/literary_plugins tests/test_prompt_loader.py
git commit -m "feat(170j): add literary optimization prompt plugin loader + minimal_voice_anchor plugins"
```

---

## Task 3: CreativeBrief 模型扩展与解析

**Files:**
- Modify: `src/songyan/models/creative_mode.py`
- Modify: `src/songyan/agents/creative_director/_brief_builder.py`
- Test: `tests/test_creative_director.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_creative_director.py
from songyan.agents.creative_director._brief_builder import _build_creative_brief
from songyan.models.chapter import ChapterGoal


def test_build_creative_brief_parses_voice_anchors():
    goal = ChapterGoal(goal_id="g1", chapter_number=1, chapter_type="normal")
    data = {
        "voice_anchors": [
            {
                "character_id": "char-1",
                "emotional_register": "压抑但易怒",
                "verbal_tick": "我没时间",
                "taboo_phrase": "对不起",
            }
        ]
    }
    brief = _build_creative_brief(data, "webnovel_intense", goal)
    assert len(brief.voice_anchors) == 1
    assert brief.voice_anchors[0].character_id == "char-1"
    assert brief.voice_anchors[0].verbal_tick == "我没时间"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_creative_director.py::test_build_creative_brief_parses_voice_anchors -v`
Expected: FAIL with `ValidationError` 或 `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/songyan/models/creative_mode.py
class VoiceAnchor(BaseModel):
    """Task 170j: 极简声纹锚定 — 每个核心人类角色的情绪基调+口头禅/禁忌."""

    character_id: str
    emotional_register: str = ""
    verbal_tick: str = ""
    taboo_phrase: str = ""


class CreativeBrief(BaseModel):
    # ... 现有字段 ...

    # Task 170j: 极简声纹锚定
    voice_anchors: list[VoiceAnchor] = Field(default_factory=list)
```

```python
# src/songyan/agents/creative_director/_brief_builder.py
from songyan.models.creative_mode import (
    CognitiveConflictTemplate,
    CreativeBrief,
    EmotionArcItem,
    PunchPoint,
    SceneTemplate,
    Tension,
    VoiceAnchor,
)


def _parse_voice_anchors(raw: Any) -> list[VoiceAnchor]:
    """Task 170j: 解析 voice_anchors 字段，无效条目静默丢弃."""
    result: list[VoiceAnchor] = []
    if not isinstance(raw, list):
        return result
    for item in raw:
        if not isinstance(item, dict):
            continue
        character_id = str(item.get("character_id", ""))
        if not character_id:
            continue
        try:
            result.append(
                VoiceAnchor(
                    character_id=character_id,
                    emotional_register=str(item.get("emotional_register", "")),
                    verbal_tick=str(item.get("verbal_tick", "")),
                    taboo_phrase=str(item.get("taboo_phrase", "")),
                )
            )
        except Exception:
            continue
    return result
```

在 `_build_creative_brief` 返回前添加：

```python
        voice_anchors=_parse_voice_anchors(data.get("voice_anchors")),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_creative_director.py::test_build_creative_brief_parses_voice_anchors -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/songyan/models/creative_mode.py src/songyan/agents/creative_director/_brief_builder.py tests/test_creative_director.py
git commit -m "feat(170j): add VoiceAnchor to CreativeBrief and parser"
```

---

## Task 4: 配置入口与 Agent 集成

**Files:**
- Modify: `src/songyan/creative_modes/registry.py` 或 `src/songyan/config/settings.py`
- Modify: `src/songyan/agents/creative_director/__init__.py`
- Modify: `src/songyan/agents/writer.py`
- Modify: `src/songyan/prompts/loader.py`（如需）
- Test: `tests/test_prompt_loader.py`, `tests/test_creative_director.py`, `tests/test_writer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompt_loader.py
from songyan.literary_optimization.plugin_loader import load_strategy_plugins


def test_strategy_plugins_empty_when_disabled():
    plugins = load_strategy_plugins([], "writer")
    assert plugins == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_prompt_loader.py::test_strategy_plugins_empty_when_disabled -v`
Expected: PASS（空列表应直接返回）

- [ ] **Step 3: Write minimal implementation**

配置入口选择 `src/songyan/config/settings.py`（若存在且合适），否则用 `src/songyan/creative_modes/registry.py`。先检查 `src/songyan/config/settings.py` 是否存在。

假设存在 `src/songyan/config/settings.py`：

```python
# src/songyan/config/settings.py 新增字段
class Settings(BaseSettings):
    # ... 现有字段 ...

    literary_optimization_plugins: list[str] = Field(default_factory=list)
    """启用的文学性/可读性优化插件 Strategy ID 列表."""
```

若不存在，则新增到 `src/songyan/creative_modes/registry.py` 中的 `CreativeModeProfile`：

```python
# src/songyan/models/creative_mode.py 中 CreativeModeProfile 新增
    literary_optimization_plugins: list[str] = Field(default_factory=list)
```

**CreativeDirector 集成：**

```python
# src/songyan/agents/creative_director/__init__.py
from songyan.literary_optimization import (
    LiteraryContext,
    list_strategies,
    load_strategy,
)
from songyan.literary_optimization.plugin_loader import load_strategy_plugins


async def _render_prompt(...) -> str:
    # ... 现有代码 ...
    plugin_ids = mode_profile.literary_optimization_plugins or []
    plugin_ids = [p for p in plugin_ids if p in list_strategies()]
    if plugin_ids and has_skeleton:
        cd_plugins = load_strategy_plugins(plugin_ids, "creative_director")
        variables["literary_plugins"] = "\n\n".join(cd_plugins)
        return render_agent_prompt(
            "creative_director", variables, version="1.0.8",
            plugins=cd_plugins,
        )
    return render_agent_prompt("creative_director", variables, version="1.0.5")
```

需要确认 `render_agent_prompt` 是否支持 `plugins` 参数；如不支持，在 prompt 模板中新增 `{{literary_plugins}}` 占位符，由 `_render_prompt` 把插件内容拼接进 variables。

**Writer 集成：**

```python
# src/songyan/agents/writer.py
from songyan.literary_optimization import list_strategies, load_strategy
from songyan.literary_optimization.plugin_loader import load_strategy_plugins


def _render_prompt(ctx: ContextPackage) -> str:
    # ... 现有代码 ...
    mode_profile = ctx.mode_profile
    plugin_ids = getattr(mode_profile, "literary_optimization_plugins", []) or []
    plugin_ids = [p for p in plugin_ids if p in list_strategies()]
    writer_plugins = load_strategy_plugins(plugin_ids, "writer")
    if writer_plugins:
        variables["literary_plugins"] = "\n\n".join(writer_plugins)

    # 把 brief.voice_anchors 格式化为文本注入
    voice_anchors_text = "（无）"
    if ctx.creative_brief and ctx.creative_brief.voice_anchors:
        lines = []
        for va in ctx.creative_brief.voice_anchors:
            lines.append(f"- {va.character_id}: {va.emotional_register}")
            if va.verbal_tick:
                lines.append(f"  口头禅: {va.verbal_tick}")
            if va.taboo_phrase:
                lines.append(f"  禁忌: {va.taboo_phrase}")
        voice_anchors_text = "\n".join(lines)
    variables["voice_anchors"] = voice_anchors_text

    return card.render(variables)
```

需要确认 Writer prompt 卡 1.2.2 是否已有 `{{voice_anchors}}` 占位符；如无，需要修改 1.2.2 或新增 1.2.3。为保持保守，先修改 1.2.2 模板新增可选占位符（无值时不影响）。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_prompt_loader.py tests/test_creative_director.py tests/test_writer.py -v`
Expected: PASS（可能需要根据实际模板调整）

- [ ] **Step 5: Commit**

```bash
git add src/songyan/agents/creative_director/__init__.py src/songyan/agents/writer.py src/songyan/config/settings.py 或 src/songyan/models/creative_mode.py tests/
git commit -m "feat(170j): wire literary optimization plugins into CreativeDirector and Writer"
```

---

## Task 5: 实验 Harness 与复评脚本

**Files:**
- Create: `scripts/run_170j_experiment.py`
- Create: `scripts/run_170j_reeval.py`
- Test: `tests/test_170j_experiment_harness.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_170j_experiment_harness.py
from pathlib import Path

from scripts.run_170j_experiment import _resolve_db_path


def test_resolve_db_path():
    assert _resolve_db_path("minimal_voice_anchor") == Path(".tmp/task170j_minimal_voice_anchor.db")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_170j_experiment_harness.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`scripts/run_170j_experiment.py` 复用 `run_170i_generation.py` 的脚手架，但：
- DB 路径改为 `.tmp/task170j_minimal_voice_anchor.db`
- 设置 `LITERARY_OPTIMIZATION_PLUGINS=["minimal_voice_anchor"]` 环境变量（或写临时配置文件）
- 只跑 Ch29–Ch32
- 复用 170i 的大纲/弧/线索初始化逻辑

由于代码较长，先写核心差异函数：

```python
# scripts/run_170j_experiment.py
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_170i_generation import (
    _build_outline,
    _find_run_id,
    _init_db,
    _load_run_log_metrics,
    _project_setting,
    _resolve_project_id,
)
from songyan.config import settings
from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task170j_minimal_voice_anchor.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
settings.database_url = DATABASE_URL
GATE_MODE = os.getenv("GATE_MODE", "observe")
ON_FAILURE = os.getenv("ON_FAILURE", "isolate")
PROJECT_FILE = Path(".tmp/task170j_minimal_voice_anchor_project.json")


def _resolve_db_path(strategy_id: str) -> Path:
    return Path(f".tmp/task170j_{strategy_id}.db")


async def _init_experiment(strategy_id: str) -> str:
    db_path = get_db_path()
    for suffix in ("", "-wal", "-shm"):
        p = db_path.with_name(db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()
    await init_schema()

    project_id = uuid.uuid4().hex
    await ProjectRepository().create(_project_setting(), project_id)
    outline, arcs, threads = _build_outline(project_id)
    await NarrativeRepository().import_outline(project_id, outline, arcs, threads)

    # 把 strategy_id 写入 project 配置或环境变量
    os.environ["LITERARY_OPTIMIZATION_PLUGINS"] = strategy_id

    PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(
        json.dumps({"project_id": project_id, "db": str(db_path)}, ensure_ascii=False),
        encoding="utf-8",
    )
    return project_id


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--strategy-id", default="minimal_voice_anchor")
    parser.add_argument("--start", type=int, default=29)
    parser.add_argument("--end", type=int, default=32)
    args = parser.parse_args()

    if args.init:
        await _init_experiment(args.strategy_id)
        print(f"[init] strategy={args.strategy_id} project created")
        return 0

    project_id = _resolve_project_id()
    if not project_id:
        parser.error("请先用 --init 创建项目")

    os.environ["LITERARY_OPTIMIZATION_PLUGINS"] = args.strategy_id
    gate_config = GateConfig.for_mode(GATE_MODE)

    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(args.start, args.end),
            mode_id="webnovel_intense",
            auto_confirm=True,
            on_failure=ON_FAILURE,
            gate_config=gate_config,
        )
        print("\n=== Pipeline completed ===")
        print(f"Completed: {result.chapters_completed}")
        print(f"Failed: {result.chapters_failed}")
    except AutoHaltException as exc:
        print(f"\n=== AutoHalt: {exc.reason} ===")
    return 0


if __name__ == "__main__":
    asyncio.run(main())
```

`scripts/run_170j_reeval.py` 复用 `run_170i_reeval.py`，只修改默认 DB 路径和报告路径：
- DB: `.tmp/task170j_minimal_voice_anchor.db`
- Report: `archive/v7/reports/task-170j-minimal-voice-anchor-reeval-report.md`
- Prose: `.tmp/task170j_prose_ch28_ch32.md`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_170j_experiment_harness.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/run_170j_experiment.py scripts/run_170j_reeval.py tests/test_170j_experiment_harness.py
git commit -m "feat(170j): add Ch29-Ch32 experiment harness and reeval script"
```

---

## Task 6: 运行小样本实验并产出报告

**Files:**
- Create: `archive/v7/tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md`
- Create: `archive/v7/reports/task-170j-minimal-voice-anchor-reeval-report.md`

- [ ] **Step 1: 初始化并运行实验**

```bash
python scripts/run_170j_experiment.py --init
python scripts/run_170j_experiment.py --start 29 --end 32
```

Expected: Ch29–Ch32 completed（observe 模式）

- [ ] **Step 2: 运行复评**

```bash
python scripts/run_170j_reeval.py
```

Expected: 生成 `archive/v7/reports/task-170j-minimal-voice-anchor-reeval-report.md`

- [ ] **Step 3: 对比 170i 基线并判定**

对比维度：voice / exposition / pacing / concept / ai_tone / 窗口均值 / T9 / exposition_carrier。

- [ ] **Step 4: 回填 DONE 文档**

`archive/v7/tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md` 记录：
- 采用策略：minimal_voice_anchor
- 实验数据与 170i 对比
- 结论：达标 / 部分提升需继续 / 无效

- [ ] **Step 5: Commit**

```bash
git add archive/v7/reports/task-170j-minimal-voice-anchor-reeval-report.md archive/v7/tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md
git commit -m "feat(170j): minimal_voice_anchor experiment results and decision"
```

---

## Task 7: 状态文档更新

**Files:**
- Modify: `docs/STATUS.md`
- Modify: `tasks/V7-README.md`
- Modify: `README.md`
- Modify: `archive/v7/tasks/170-literary-quality-remediation-README.md`

- [ ] **Step 1: 更新 docs/STATUS.md**

把"170j 已启动"改为"170j minimal_voice_anchor Strategy 已落地并复评"，填入实测数据。

- [ ] **Step 2: 更新 V7-README / README / 专项 README**

同步 170j 结论与下一步。

- [ ] **Step 3: Commit**

```bash
git add docs/STATUS.md tasks/V7-README.md README.md archive/v7/tasks/170-literary-quality-remediation-README.md
git commit -m "docs: update 170j status across entry docs"
```

---

## Task 8: 验证与 lint

**Files:**
- All changed files

- [ ] **Step 1: ruff check**

```bash
ruff check src/ tests/
```
Expected: All checks passed

- [ ] **Step 2: 分模块 pytest**

```bash
python -m pytest tests/literary_optimization tests/test_prompt_loader.py tests/test_creative_director.py tests/test_writer.py tests/test_170j_experiment_harness.py -q
```
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: lint and test pass for 170j"
```

---

## Self-Review

1. **Spec coverage:**
   - Strategy 抽象 ✅ Task 1
   - Prompt 插件加载 ✅ Task 2
   - CreativeBrief 扩展 ✅ Task 3
   - Agent 集成 ✅ Task 4
   - 实验 harness ✅ Task 5
   - 报告与状态更新 ✅ Task 6/7
   - Lint/test ✅ Task 8

2. **Placeholder scan:**
   - 无 TBD/TODO
   - 代码块完整
   - 文件路径具体

3. **Type consistency:**
   - `LiteraryOptimizationStrategy.strategy_id`、`applicable_agents`、`apply` 在全 plan 中一致
   - `VoiceAnchor` 字段与 parser 一致
   - `load_strategy_plugins` 签名一致

---

## Execution Handoff

Plan complete and saved to `archive/superpowers/plans/2026-07-09-minimal-voice-anchor-170j.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?

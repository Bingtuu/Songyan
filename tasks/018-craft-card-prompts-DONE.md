# Task 018: Craft Card Prompts — 交接报告

## 做了什么

实现 Craft Card Prompt 工程系统，将 7 个扁平 `.md` Prompt 模板升级为结构化、版本化、可观测的 YAML 工艺卡。

## 改动的文件

### 新增源码
- `src/songyan/prompts/__init__.py` — 公共 API 导出（get_prompt_loader, reset_prompt_loader, PromptLoader, 所有模型）
- `src/songyan/prompts/_models.py` — Pydantic 模型（CraftCard, CraftCardSection, Manifest, RenderedPrompt 等）
- `src/songyan/prompts/loader.py` — PromptLoader（模块级单例、文件扫描、缓存、Jinja2 渲染、结构化日志）

### 新增工艺卡
- `prompts/cards/writer/_manifest.yaml` + `1.0.0.yaml` — Writer 工艺卡（8 个结构化模块）
- `prompts/cards/goal_planner/_manifest.yaml` + `1.0.0.yaml`
- `prompts/cards/creative_director/_manifest.yaml` + `1.0.0.yaml`
- `prompts/cards/llm_auditor/_manifest.yaml` + `1.0.0.yaml`
- `prompts/cards/literary_auditor/_manifest.yaml` + `1.0.0.yaml`
- `prompts/cards/revision_handler/_manifest.yaml` + `1.0.0.yaml`
- `prompts/cards/settlement_extractor/_manifest.yaml` + `1.0.0.yaml`

### 迁移文件
- `prompts/*.md` → `prompts/archive/*.md`（7 个旧模板归档）

### 改造 Agent
- `src/songyan/agents/writer.py` — `_render_prompt` 使用 PromptLoader，传入 tags 激活条件模块
- `src/songyan/agents/goal_planner.py` — `_load_prompt_template` 使用 PromptLoader
- `src/songyan/agents/creative_director.py` — `_load_prompt_template` 使用 PromptLoader
- `src/songyan/agents/llm_auditor.py` — `_render_prompt` 使用 PromptLoader
- `src/songyan/agents/literary_auditor.py` — `_render_prompt` 使用 PromptLoader
- `src/songyan/agents/revision_handler.py` — `_render_prompt` 使用 PromptLoader
- `src/songyan/agents/settlement_extractor.py` — `_render_prompt` 使用 PromptLoader

### 新增测试
- `tests/test_prompt_loader.py` — 18 个测试（加载、渲染、标签过滤、缓存、单例、Agent 集成）

### 其他
- `pyproject.toml` — 添加 `pyyaml>=6.0` 依赖
- `tasks/018-craft-card-prompts.md` — Task 规格

## 如何运行

```bash
# 运行 PromptLoader 测试
pytest tests/test_prompt_loader.py -v

# 运行全部测试
pytest tests/ -v

# 代码风格检查
ruff check src/ tests/
```

## 验证结果

- `pytest tests/test_prompt_loader.py`：**18 passed, 0 failed**
- `pytest`（全量）：**595 passed, 0 failed**（577 原有 + 18 新增）
- `ruff check`：**0 errors**

## Writer 工艺卡 8 个模块

| 模块 ID | 条件标签 | 说明 |
|---------|---------|------|
| golden_opening | chapter_early | 前 300 字吸引力法则 |
| paragraph_rhythm | — | 段落长度分布控制 |
| dialogue_craft | — | 对话区分度与潜台词 |
| show_dont_tell | — | 感官/动作替代情绪陈述 |
| info_release | — | 新信息节奏控制 |
| sensory_immersion | — | 多感官场景描写 |
| ending_hook | — | 最后 200 字有效悬念 |
| new_setting_mark | — | 新设定显式标记 |

## 已知限制

1. **条件逻辑仅支持标签匹配**：不能执行 `chapter_number <= 3` 这类计算，条件由调用方通过 `tags` 参数控制
2. **无 A/B 测试**：版本切换需手动修改 `_manifest.yaml` 的 `default_version`，或跑评测集对比
3. **examples 未实现**：few-shot 示例当前为空，后续可添加独立 `examples/` 目录
4. **Writer 之外无 sections**：其他 6 个 Agent 的 YAML 只有 `system_prompt`，未拆分模块

## 还没做什么

- Task 019: LangGraph 编排 + SummaryWriter
- 集成测试 + 评测集
- Craft Card 的在线编辑/热重载 UI

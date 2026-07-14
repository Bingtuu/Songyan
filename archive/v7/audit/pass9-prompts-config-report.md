# Pass 9: Prompt 与配置管理审计报告

## 执行摘要

- 发现总数: 3
- P0: 0, P1: 0, P2: 3
- 关键结论: Prompt 工艺卡版本管理体系成熟，`PromptLoader` 使用 `SandboxedEnvironment` 并做 Jinja2 定界符转义；Genre/Mode 加载器有明确错误和缓存机制。主要残留问题是 `revision_handler` 中仍有 2 处内联 Prompt 字符串，以及工艺卡版本与代码默认版本的一致性需定期核对。

## 检查项与发现

### 9.1 代码内嵌 Prompt 扫描

- **级别**: P2
- **方法**: `rg 'def build_.*_prompt|prompt = """|prompt = f"""|system_message = ' src/songyan/ -n`
- **结果**:
  - `src/songyan/agents/revision_handler/__init__.py:365` — `prompt = f"""你是小说编辑。以下章节场景过多且字数超标，需要合并次要场景。`...
  - `src/songyan/agents/revision_handler/_segmented_revision.py:180` — `prompt = f"""你是小说修订助手。请根据以下问题列表，修改给定的场景段落。`...
- **问题描述**: 两处 Prompt 直接写在代码中，违反“Prompt 放在 `prompts/` 目录，代码中不写长 prompt”的规范。虽然这些属于小众修复路径，但随着版本迭代容易与工艺卡脱节。
- **修复建议**: 将这两处 Prompt 提取为 `prompts/cards/revision_handler/` 下的新工艺卡版本（如 `1.1.0`），通过 `PromptLoader` 加载。

### 9.2 Prompt 工艺卡版本管理

- **级别**: 通过
- **文件**: `prompts/cards/`, `src/songyan/prompts/loader.py`
- **方法**: 检查 manifest 结构和 loader 实现
- **结果**:
  - 10 个 Agent 目录均有 `_manifest.yaml`。
  - `PromptLoader` 扫描 `_manifest.yaml`，支持 `default_version` 和按版本加载。
  - 渲染结果缓存 60 秒，自动清理过期条目。
  - 校验必需变量，缺失时抛出明确 `ValueError`。
- **结论**: 工艺卡版本管理机制成熟。

### 9.3 Jinja2 模板注入防护

- **级别**: 通过
- **文件**: `src/songyan/prompts/loader.py:27-39, 199-200`
- **方法**: 检查是否使用沙箱环境和转义
- **结果**:
  - 使用 `jinja2.sandbox.SandboxedEnvironment`。
  - `_escape_jinja2` 将 `{{` 替换为 `\{\{`、`{%` 替换为 `\{%`。
- **结论**: 模板注入防护到位。

### 9.4 Genre / Mode 配置加载

- **级别**: 通过
- **文件**: `src/songyan/genres/loader.py`, `src/songyan/creative_modes/registry.py`
- **方法**: 检查缺失文件处理和校验
- **结果**:
  - `load_genre_profile` 在文件不存在时抛出 `GenreProfileNotFoundError` 并列出可用 genres。
  - `load_creative_mode_profile` 同理。
  - 两者均校验 `active_audit_dimensions` 是否来自 `ReviewCategory`。
  - 均支持 `set_*_dir` 用于测试覆盖。
- **结论**: 配置加载健壮，变更无需改代码。

### 9.5 Prompt 版本与代码版本一致性

- **级别**: P2
- **方法**: 抽样检查代码中使用的默认版本与 manifest 中 `default_version` 是否一致
- **结果**:
  - Writer manifest `default_version: "1.1.0"`；代码中 `render_agent_prompt("writer", ...)` 通常不传 version，使用 default。
  - 但 `revision_handler` 中两处内联 Prompt 绕过了工艺卡版本管理。
- **建议**: 增加一项回归测试，确保所有 Agent 的 default_version 与代码中显式版本（如有）一致；禁止新增内联 Prompt。

### 9.6 工艺卡 tags 使用

- **级别**: P2
- **方法**: 检查 `get_active_sections` 是否被使用
- **结果**: `PromptLoader.get_active_sections` 支持按 tags 过滤 section，但当前代码中调用 `render_card` 时 tags 参数使用较少。
- **建议**: 若 V7/V8 需要按题材/模式动态裁剪 Prompt section，可在 `render_agent_prompt` 中统一传入 tags，避免为每个变体新建工艺卡版本。

## 通过项

- [x] Prompt 统一放在 `prompts/cards/`。
- [x] `PromptLoader` 支持版本管理和缓存。
- [x] 使用 `SandboxedEnvironment` 并转义 Jinja2 定界符。
- [x] Genre/Mode 加载器有明确错误和校验。

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 9.1 | P2 | `revision_handler` 有 2 处内联 Prompt | `src/songyan/agents/revision_handler/__init__.py`, `_segmented_revision.py`, `prompts/cards/revision_handler/` | `pytest tests/test_revision_handler.py -q` |
| 9.5 | P2 | 缺少工艺卡版本一致性回归测试 | 新增 `tests/test_prompt_version_consistency.py` | `pytest tests/test_prompt_version_consistency.py -q` |
| 9.6 | P2 | tags 过滤能力未充分利用 | `src/songyan/prompts/loader.py` 使用方 | 文档/示例 + 测试 |

---

> 下一 Pass: [Pass 10 性能与可观测性审计](pass10-performance-observability-report.md)

# Pass 11: 安全与依赖审计报告

## 执行摘要
- **发现总数**: 5
- **P0**: 0, **P1**: 0, **P2**: 5
- **关键结论**: 无事实源污染或注入漏洞；依赖声明基本完整，但 `json_repair` 未在 `pyproject.toml` 中声明（有手动 fallback，影响可控）；CLI 输入验证与凭证处理符合要求；repository 层以参数化查询为主，仅存在内部常量/枚举驱动的 f-string SQL，当前风险低。

## 检查项与发现

### 11-1 `json_repair` 未声明为项目依赖
- **级别**: P2
- **文件**: `src/songyan/llm/parsing.py:139`, `pyproject.toml:24-39`
- **问题描述**: `parse_llm_response` 在标准 `json.loads` 失败后，优先尝试 `from json_repair import repair_json`。该第三方库未在 `pyproject.toml` 的 `dependencies` 中列出。虽然函数提供了无库时的手动修复 fallback，但在干净环境中安装项目后将缺失该增强路径。
- **证据**:
  ```python
  # src/songyan/llm/parsing.py:139
  from json_repair import repair_json
  ```
  `pyproject.toml` dependencies 中无 `json_repair`。
- **潜在影响**: 在新环境首次安装时，LLM JSON 修复能力降级为手动修复，可能降低对 LLM 不规则 JSON 的容错率。
- **修复建议**: 在 `pyproject.toml` `[project] dependencies` 中添加 `"json-repair>=0.20"`（或当前兼容版本），并保留手动 fallback 作为降级保护。
- **验证方式**: `python -c "import json_repair; print(json_repair.__version__)"` 在干净 venv 中应成功。

### 11-2 `lifecycle_scheduler.transition` 接受外部表名并用于 f-string SQL
- **级别**: P2
- **文件**: `src/songyan/db/lifecycle_scheduler.py:94-136`, `src/songyan/db/lifecycle_scheduler.py:218-227`
- **问题描述**: `LifecycleScheduler.transition(..., table: str, ...)` 是类公开方法，其 `table` 与内部推导的 `pk_col` 被直接拼接到 SQL 字符串中。当前调用方均来自 `_LIFECYCLE_TABLES` 与 `_cleaners` 内部注册表，未使用用户输入，但接口本身未对 `table` 做白名单校验，存在误用风险。
- **证据**:
  ```python
  # src/songyan/db/lifecycle_scheduler.py:109-111
  pk_col = _primary_key_column(table)
  cursor = await conn.execute(
      f"SELECT lifecycle_status FROM {table} WHERE {pk_col} = ?",  # noqa: S608
      (entity_id,),
  )
  ```
- **潜在影响**: 若未来有调用方将用户可控字符串传入 `table`，可导致 SQL 注入。
- **修复建议**: 在 `transition` 入口增加 `table` 白名单校验（`table in _LIFECYCLE_TABLES` 或注册 cleaner 表名集合），并同样校验 `_primary_key_column` 返回值存在；否则抛出 `ValueError`。
- **验证方式**: 新增单测断言非法表名调用 `transition` 时抛出异常而非执行 SQL。

### 11-3 `continuity_repo` 动态构建 SQL 类别子句
- **级别**: P2
- **文件**: `src/songyan/db/continuity_repo.py:292-336`
- **问题描述**: `archive_long_silent_nonessential` 通过遍历 `LONG_SILENT_ARCHIVE_WINDOWS` 字典动态拼接 `category_clause`，并作为 f-string 注入到 SQL 中。字典键为内部常量，且数值位置使用参数化，当前安全；但代码风格上混合了字符串拼接与参数化。
- **证据**:
  ```python
  category_clause = " OR ".join(clauses)
  # ...
  f"""UPDATE setting_tracking ... AND ({category_clause}) ..."""
  ```
- **潜在影响**: 若 `LONG_SILENT_ARCHIVE_WINDOWS` 键未来被外部化或误改为用户输入，将引入注入风险。
- **修复建议**: 对 `LONG_SILENT_ARCHIVE_WINDOWS` 键做白名单校验，或在注释中明确其“内部常量、禁止外部输入”的契约。
- **验证方式**: 代码审查 + ruff `S608` 检查。

### 11-4 `evals/__main__.py` 使用 `print` 而非 `structlog`
- **级别**: P2
- **文件**: `src/songyan/evals/__main__.py:121-176`
- **问题描述**: 该 CLI 模块直接使用 `print(...)` 输出报告进度与错误，与项目“日志用 structlog，不用 print”的规范不一致。作为独立 CLI 工具，其对用户可读输出尚可接受，但错误信息应优先走 `structlog`/`stderr` 统一通道。
- **证据**:
  ```python
  print(f"从 {jsonl_path} 读取了 {len(logs)} 条日志")
  print(f"报告已生成: {output_path}")
  ```
- **潜在影响**: 日志上下文（`run_id`、`project_id`）无法结构化关联；输出无法被统一日志收集器处理。
- **修复建议**: 将进度/结果信息改用 `structlog.get_logger()`，保留 `file=sys.stderr` 的错误输出；或显式标注该模块为“面向终端的 CLI 报告器”并在 `AGENTS.md` 中例外说明。
- **验证方式**: `rg '^\s*print\(' src/songyan/evals/__main__.py -n` 命中数降为 0。

### 11-5 `call_llm` 未返回 token 用量与 request_id
- **级别**: P2
- **文件**: `src/songyan/llm/client.py:154-234`
- **问题描述**: `call_llm` 仅返回文本字符串，不暴露 token 用量、模型响应 `usage` 或请求追踪 ID。长窗口成本估算、T12 标定与可观测性均依赖该数据，目前已通过下游估算或日志旁路弥补。
- **证据**:
  ```python
  async def call_llm(prompt: str, ...) -> str:
      ...
      return str(response.content)
  ```
- **潜在影响**: 无法精确核算 Ch200+ 长跑成本；无法关联 LLM 提供方的调用链；T12 与 T5 冻结报告中的 token 数据为估算值。
- **修复建议**: 将 `call_llm` 返回类型升级为包含 `content: str`、`usage: TokenUsage | None`、`request_id: str | None` 的 Pydantic 模型；同步调整所有调用点（或提供新的 `call_llm_with_usage` 接口并保持旧接口兼容）。
- **验证方式**: 新增/更新 `tests/test_llm_client.py` 断言返回对象包含 `usage` 字段。

## 通过项

| 检查项 | 结论 | 证据 |
|--------|------|------|
| 依赖声明完整性 | 基本通过 | `jinja2>=3.1`、`pyyaml>=6.0`、`tiktoken`、`sentence-transformers>=2.7.0`、`litellm>=1.40`、`langchain>=0.3`、`langgraph>=0.2`、`pydantic>=2.0` 均已声明 |
| 环境变量与凭证 | 通过 | `.env.example` 列出 `LLM_API_KEY` 等关键变量；`src/songyan/config.py` 用 `pydantic-settings` 加载；`.gitignore` 忽略 `.env`、`*.{db,sqlite,sqlite3}` |
| API key 不记录 | 通过 | `src/songyan/llm/client.py` 仅将 `api_key` 传入 `ChatLiteLLM`，日志中不输出 key；`_get_llm_cached` 的缓存 key 包含 api_key，但 lru_cache 在内存中不外泄 |
| CLI 参数校验 | 通过 | `create-project --outline-file` 使用 `click.Path(exists=True)`；`run --chapters` 在命令内解析为整数范围；`--gate-mode/--rag-mode/--on-failure` 使用 `click.Choice`；`mark_add --priority` 做 `max(1, min(10, priority))` 边界裁剪 |
| 大纲导入校验 | 通过 | `src/songyan/cli/outline_import.py` 对 JSON 结构、字段类型、`thread_id` 唯一性、弧-线索引用做完整校验，并转换为 Pydantic 模型 |
| 反序列化安全 | 通过 | 全库使用 `json.loads`/`json.dumps` 与 `yaml.safe_load`；未搜索到 `pickle`、`yaml.load`（unsafe）用法 |
| 核心 repository 参数化 | 通过 | `chapter_versions` 仅更新元数据字段（`is_abandoned`、`version_type`、`score_card`），不更新 `content`；`character_states` 的 `UPDATE` 仅限 `lifecycle_status`，且由内部 state_id 列表驱动 |
| 无 SQL 注入用户路径 | 通过 | 用户输入（project_id、chapter_number、outline JSON 字段）均通过 `?` 占位符传递；f-string SQL 仅用于内部生成的 `?` 占位符列表、内部表名/列名/类别常量 |

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 11-1 | P2 | `json_repair` 未声明依赖 | `pyproject.toml` | `python -c "import json_repair"` 在干净 venv |
| 11-2 | P2 | `lifecycle_scheduler.transition` 表名未白名单 | `src/songyan/db/lifecycle_scheduler.py` | 新增非法表名单测 |
| 11-3 | P2 | `continuity_repo` 类别子句动态拼接 | `src/songyan/db/continuity_repo.py` | 代码审查 + ruff |
| 11-4 | P2 | `evals/__main__.py` 使用 print | `src/songyan/evals/__main__.py` | `rg '^\s*print\(' src/songyan/evals/__main__.py` |
| 11-5 | P2 | `call_llm` 未返回 token/request_id | `src/songyan/llm/client.py` | `pytest tests/test_llm_client.py -v` |

---
> 审计结论：无 P0/P1 安全或依赖缺陷，可在完成 P2 清理后进入 Task 170 / Ch200 爬坡。

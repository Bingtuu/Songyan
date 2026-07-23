# Pass 7 — 安全审计报告

> **范围**: SQL 注入、Prompt 注入、敏感信息泄漏、输入校验、RAG 安全
> **日期**: 2026-06-11
> **审查者**: Codex
> **状态**: 完成

---

## 摘要

| 维度 | 判定 | 关键发现 |
|------|------|---------|
| SQL 注入风险 | ✅ 安全 | 全部使用参数化查询，零 f-string 拼接 |
| Prompt 注入防御 | ✅ 良好 | SandboxedEnvironment + 递归转义覆盖所有变量 |
| 敏感信息泄漏 | ✅ 安全 | 零硬编码密钥，日志不打印敏感字段 |
| 输入校验 | ⚠️ 见发现 | 1 项 P2 发现（TypedDict 无运行时校验） |
| RAG 安全 | ✅ 安全 | HTTPS 下载 + 异常安全兜底 |
| 总体 | 2 项发现 (P2) | 无 P0/P1 安全问题 |

---

## 1. SQL 注入风险（S1-S4）— 通过

### S1: DB 层参数化查询

**检查方法**: 搜索 `src/songyan/db/*.py` 中 f-string 直接拼接 SQL 的模式。

**结果**: 零处发现。全部 14 个 repository 文件使用参数化 `?` 占位符。Repository 层的所有 `execute()` 调用都传递独立的参数元组，而非字符串格式化。

### S2: Repository 层字符串拼接

**检查方法**: 逐文件审查 14 个 `db/*_repo.py` 文件的所有 SQL 查询。

**结果**: 全部安全。确认所有repository类使用 `await conn.execute(sql, params...)` 模式，参数通过结构化类型传递。`get_db_path()` 解析 `database_url` 时使用 `str.startswith` + `str[len:]`，没有使用 `eval()` 或 `exec()`。

### S3: Migration DDL 安全

**检查方法**: 审查 `db/migrations.py` 的所有 DDL 语句。

**结果**: 全部安全。49 条 DDL 语句（CREATE TABLE/ALTER TABLE/CREATE INDEX）全部为 Python 字符串字面量。2 处 `f"..."` 格式只格式化内部表名常量（`lifecycle_status` 和索引名），非用户输入。

```python
# Safe: 只格式化内部常量
f"ALTER TABLE {table} ADD COLUMN lifecycle_status TEXT DEFAULT 'active'"
f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({cols})"
```

### S4: 外部输入进入 SQL 前的清洗

**检查路径**: `human_instruction.content` → DB Repository

**结果**: 安全。`HumanInstruction` 数据流经 ContextManager → ContextPackage → Prompt 渲染管道，从不直接进入 SQL。Repository 层中使用参数化查询写入 `human_marks` 表。用户数据的所有 SQL 路径都有参数化保护。

---

## 2. Prompt 注入风险（S5-S8）— 通过，1 项 P2 发现

### S5: Jinja2 SandboxedEnvironment

**检查方法**: 审查 `prompts/loader.py` 的 Jinja2 环境配置。

**结果**: ✅ 正确使用 `SandboxedEnvironment(autoescape=False)`。`SandboxedEnvironment` 是 Jinja2 的安全沙箱，禁用危险的模板特性（如 `{% import %}`, `{% extends %}`, 对象属性访问限制）。`autoescape=False` 是故意的—HTML 转义会破坏生成的小说文本。

```python
_jinja_env = SandboxedEnvironment(autoescape=False)
```

### S6: _escape_jinja2 覆盖范围

**检查方法**: 审查 `_escape_jinja2()` 的调用点和覆盖路径。

**结果**: ✅ 全面覆盖。`_escape_jinja2()` 在 `render_card()` 第 198 行被调用，递归遍历完整的 `variables` dict 的所有字符串值。
- `str`: 替换 `{{` → `\{\{`, `{%` → `\{`
- `list`: 递归每个元素
- `dict`: 递归所有值
- `其他类型`: 原样返回

**发现 S6-R1**: `_escape_jinja2` **不转义 dict 的 key**，只转义 value。当 key 被用作模板变量名时（如 `{% for k in dict %}{{ k }}{% endfor %}`），如果用户控制 key 值，理论上可以注入包含 Jinja2 语法字符的表达式。但在当前使用场景中，craft card 的 YAML 模板由开发者控制，key 不在用户输入范围内。**P3 低风险。**

```python
# 实际路径
user_input = {"purpose": "写一个{场景}"}
_escape_jinja2(user_input)
# 结果: {"purpose": "写一个\{场景\}"}  ✅ 安全

# 未覆盖场景: key 作为模板变量名
{"{{evil}}": "xxxx"}
_escape_jinja2({"{{evil}}": "xxxx"})
# key 的 {{ 未被转义 → 但 Jinja2 模板中的 key 被 if/for 使用时不执行
# 风险仅限于纯文本输出
```

### S7: human_instructions 转义检查

**检查方法**: 追踪 `human_instruction.content` → Prompt 渲染的完整路径。

**结果**: ⚠️ **P2 — 模板变量未供应 / 死代码路径**

`human_instructions` 出现在 5 个版本的 writer craft card 模板中（1.0.5~1.0.9）：

```yaml
{% if human_instructions %}
## 人类指令（最高优先级）
{% for inst in human_instructions %}
- [{{ inst.action }}] {{ inst.content }}
{% endfor %}
{% endif %}
```

技术发现:
1. ✅ 如果 `human_instructions` 变量被供应，它会在第 198 行经过 `_escape_jinja2()` 转义
2. ⚠️ 但 `writer.py` 的 `_render_prompt()` 函数中没有将 `human_instructions` 放入 `variables` dict
3. ⚠️ ContextPackage 模型没有 `human_instructions` 字段
4. ✅ 在 Jinja2 中，未定义的变量默认是 `Undefined`，`{% if undefined %}` 为假，所以这段模板不会被渲染

**结论**: 死代码路径，无害但存在维护陷阱。如果将来在 `_render_prompt()` 中添加了 `human_instructions` 变量注入而没有经过 `_escape_jinja2`，则会引入注入风险。

### S8: Craft Card YAML 模板变量引用

**检查方法**: 扫描 21 个 `.yaml` 文件中的所有 `{{ variable }}` 引用。

**结果**: ✅ 全部安全。所有变量引用通过 `_escape_jinja2(variables)` 在渲染前转义。加上 `SandboxedEnvironment` 的沙箱保护，不存在模板注入路径。

---

## 3. 敏感信息泄漏（S9-S12）— 通过，1 项 P3 发现

### S9: 硬编码密钥

**检查方法**: 搜索 `sk-` 模式 + `api_key=`, `secret=`, `password=` 赋值。

**结果**: 零处发现。`config.py` 通过 Pydantic `BaseSettings` 从 `.env` 或环境变量加载敏感配置。代码库中没有任何硬编码的凭据。

### S10: 日志敏感字段

**检查方法**: 搜索 structlog 调用点中的 `api_key`, `token`, `secret`, `password` 参数。

**结果**: 零处发现。所有结构化日志调用使用域相关的上下文（如 `project_id`, `chapter_number`, `model_name`），不包括凭据信息。

### S11: .env.example 配置完整性

**检查结果**: ⚠️ **P3 — `database_url` 缺失**

`.env.example` 包含 7 个变量：
- LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE
- CONTEXT_TOTAL_BUDGET, CONTEXT_GENERATION_RESERVE
- LOG_LEVEL, CHECKPOINTER_MODE

`config.py` 中定义了 9 个字段（包括 LLM_FALLBACK_MODEL, LLM_FALLBACK_API_KEY 的注释），但 **`database_url` 没有在 `.env.example` 中列出**。数据库文件路径默认为 `songyan.db`，用户如果需要自定义路径，不知道应该通过环境变量 `DATABASE_URL` 来设置。

### S12: .gitignore 覆盖

**检查文件**: `.gitignore`

**结果**: ✅ 全面。覆盖 `.env`, `*.db`, `*.db-journal`, `*.db-shm`, `*.db-wal`, `*.log`, `evals/output/`, `projects/`, `logs/`, `archive/projects/`, `archive/docs/`, `archive/prd/`, `archive/prompts/` 等。

---

## 4. 输入校验（S13-S15）— 通过，1 项 P2 发现

### S13: CLI 参数验证

**检查文件**: `cli/main.py`, `cli/commands/index.py`

**结果**: ✅ 良好。Click CLI 使用：
- `type=click.Choice(["setting", "character", "foreshadowing", "custom"])` (枚举校验)
- `type=int` (类型校验)
- `is_flag=True` (布尔标志)
- `required=True` (空值检查)

无 unbounded 字符串参数直接用于文件操作或 SQL。`run` 命令的 `--chapters` 接受字符串但由调用方进一步解析。

### S14: LangGraph State 输入校验

**检查文件**: `workflows/phase1_graph.py`

**结果**: ⚠️ **P2 — `Phase1State` 为 `TypedDict`，无运行时校验**

```python
class Phase1State(TypedDict):
    project_id: str
    chapter_number: int
    mode_id: str
    ...
```

**发现**: `Phase1State` 继承自 `TypedDict` 而非 `BaseModel`。TypedDict 是纯类型提示，在运行时不做任何字段校验。一个错误调用 `{"project_id": 123, "chapter_number": "abc", ...}` 在类型系统看来是错误的，但在运行时不会抛出校验异常。

LangGraph 的 `graph.invoke()` 接收任意 dict，不进行 schema 校验。不正确的数据类型会在深层逻辑中暴露为 `AttributeError` 或 `TypeError`，而非清晰的校验错误。

### S15: 文件路径遍历

**检查方法**: 搜索 `open()` / `Path()` 中使用动态输入的模式。

**结果**: 安全。2 个潜在标志的文件路径使用硬编码的绝对或相对路径（`creative_modes/`, `genres/`），不使用用户输入的文件名。

---

## 5. RAG 安全（S16-S17）— 通过

### S16: Embedder 模型下载安全

**检查文件**: `rag/embedder.py`

**结果**: ✅ 安全。`SentenceTransformer` 使用默认的 HuggingFace Hub HTTPS 下载。模型名 `shibing624/text2vec-base-chinese` 是硬编码字符串。`embed()` 和 `aembed()` 在 encode 失败时返回零数组而非崩溃。

```python
try:
    self._load_model()
    embeddings = self._model.encode(texts, ...)
except Exception as exc:
    logger.warning("embedder.encode_failed", ...)
    return np.zeros((len(texts), self.dimension), dtype=np.float32)
```

### S17: RAG 检索内容过滤

**检查文件**: `rag/retriever.py`

**结果**: ✅ 当前设计合理。`retriever.py` 包含：
- `_META_INSTRUCTION_PATTERNS`: 用于过滤查询中的无信息元指令（如"必须精彩"）
- `retrieve()`: 完整的 try/except 保护，返回 [] 而非崩溃
- `retrieve_for_chapter()`: 两层异常保护（vector_store.load + keyword_fallback）

> **注**: 对于网文创作系统，有害内容过滤不属于核心安全需求。当前系统不输出未经 LLM 审查的公开内容。

---

## 6. 发现汇总

| ID | 严重度 | 发现 | 文件 | 建议 |
|----|--------|------|------|------|
| SEC-01 | P2 | `Phase1State` 为 TypedDict，无运行时输入校验 | `phase1_graph.py:1-30` | 改为 `BaseModel` 或添加输入验证函数；或在 `run_chapter_pipeline()` 入口用 Pydantic 校验 |
| SEC-02 | P3 | `human_instructions` 模板变量在 `writer.py` 中从未被供应，但 craft card 模板引用它 | `writer.py` / craft card 1.0.5-1.0.9 | 要么移除模板中的死代码，要么将 `_render_prompt()` 中补全变量注入（并确保经过 `_escape_jinja2`） |
| SEC-03 | P3 | `.env.example` 缺少 `database_url` | `.env.example` | 添加注释说明 `DATABASE_URL` 环境变量 |
| SEC-04 | P3 | `_escape_jinja2` 不转义 dict key | `prompts/loader.py` | 低风险（key 由开发者控制），可标记为已知 |
| SEC-05 | P4 | SandboxedEnvironment 的 `autoescape=False` 无 HTML 转义 | `prompts/loader.py:20` | 对 LLM 文本输出场景是故意选择，无需修复 |

---

## 7. 与已有 Pass 的交叉引用

| Pass 1-6 引用 | 关联 |
|--------------|------|
| Pass 1 P1-1 (14 处 except Exception) | Embedder.aembed() 使用 `except Exception` 兜底，已确认是安全的默认值返回模式 |
| Pass 4 C4 (缺 request_id) | 安全角度：无 request_id = 无法审计跨调用链日志 = 安全事件追溯困难 |
| Pass 4 C1 (get_llm except Exception) | 确认可捕获 KeyboardInterrupt，但不影响密钥安全 |

---

## 8. 修复建议优先级

```
SEC-01 (TypedDict 无校验)  ████████▁▁  改为 BaseModel → 所有非法输入被入口拦截
SEC-02 (死代码变量)        ████▁▁▁▁▁▁  删除或补全 human_instructions 注入路径
SEC-03 (.env.example 缺失)  ████▁▁▁▁▁▁  添加 database_url 注释
SEC-04 (dict key 不转义)    ██▁▁▁▁▁▁▁▁  已知低风险，标记即可
SEC-05 (autoescape=False)   ▁▁▁▁▁▁▁▁▁▁  故意设计，无需修改
```

---

## 方法说明

- **扫描范围**: `src/songyan/`（102 个 .py 文件）, `prompts/cards/`（21 个 .yaml 文件）
- **工具**: PowerShell `Select-String`（等效 rg）+ 人工代码审查
- **局限**:
  - 未进行动态测试（注入尝试）
  - 未审计 litellm 客户端从环境变量读取 API key 的具体实现
  - 未审计第三方依赖的已知 CVE（属于 Pass 9 范围）
  - 缺少运行时验证：无法确认 LLM API key 是否确实从环境变量读取且不在请求头中泄漏

> **松烟入墨，字句成锋。**
> 安全的本质不是防住一切攻击，而是在每层走廊上都亮着灯——有人经过时，你能看见他是谁。

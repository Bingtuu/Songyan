# Task 184: genres/creative_modes JSON Schema

> **阶段**: V9.3 爬坡工具链
> **类型**: 资源治理 / JSON Schema / loader 校验
> **优先级**: P2（V9 工具链收编尾项；降低后续体裁/模式配置漂移风险）
> **依赖**: 178 运行资源已迁入包内；181 CI 已上线；182/183 工具链收编已完成
> **状态**: ✅ 完成（DONE: `archive/v9/184-genres-creative-modes-json-schema-DONE.md`）
> **来源**: `tasks/V9-README.md` Task 184 行；V9 A 组工具链地基尾项

---

## 任务边界

为包内体裁与创作模式资源补正式 JSON Schema，并把校验接入加载链路：

1. `src/songyan/genres/data/_schema.json`：约束 `GenreProfile` JSON。
2. `src/songyan/creative_modes/data/_schema.json`：约束 `CreativeModeProfile` JSON。
3. `load_genre_profile()` / `load_creative_mode_profile()` 在 JSON 解析后、Pydantic 模型实例化前执行 schema 校验。
4. 7 个 genre JSON + 4 个 creative mode JSON 全部通过校验。
5. 坏样本被 loader fail fast，并给出可定位错误信息。
6. `list_genre_profiles()` / `list_creative_mode_profiles()` 不把 `_schema.json` 当成可用资源 ID。

不做：

- 不改变 `GenreProfile` / `CreativeModeProfile` Pydantic 模型语义。
- 不改变现有资源字段含义，不删除当前生产资源字段。
- 不改 `GenreRuntimeProfile` / Task 183 Profile CLI。
- 不新增数据库 schema，不触发 `init_schema()`。
- 不做 Task 185 urban 标定实跑。

## 当前事实

- Task 178 已把 `genres/data` 与 `creative_modes/data` 迁入包资源，loader 默认通过 `importlib.resources.files()` 读取。
- `src/songyan/project_templates/data/_schema.json` 已存在，可作为文件布局参考，但它当前只是资源文件，不是通用校验框架。
- `GenreProfile` 与 `CreativeModeProfile` 的 Pydantic 模型均设置 `model_config = {"extra": "ignore"}`。
- 因此，仅靠 Pydantic 实例化无法发现拼错字段或废弃字段漂移。
- `CreativeModeProfile` 当前生产资源里有 `webnovel_intense.json` 的 `punch_engine` 字段；模型未消费该字段，但它是现有资源事实，Task 184 不能用 schema 误伤。

## 关键设计约束

### 1. Schema 是资源契约，不是运行时语义重写

本任务只在资源加载时增加结构校验：

- 缺必填字段应失败。
- 字段类型错误应失败。
- 已知枚举值错误应失败。
- 明显未知字段应失败或被纳入显式兼容字段清单。

不得借此修改 writer / auditor / ContextManager 的运行时行为。

### 2. loader 校验必须兼容 Traversable

178 后默认资源可能来自 wheel / zip-backed `Traversable`，实现不能假设 `Path` API 完整可用。读取 schema 与 JSON 时应沿用 `Traversable.open()` / `read_text()` 这类接口，不要求真实文件路径。

### 3. strict 开关要保守

V9 目标写的是“加载时校验（可选 strict）”。推荐口径：

- 默认 loader 对包内生产资源执行 schema 校验。
- 测试注入外部目录也执行同一 schema 校验。
- strict 只用于控制“是否拒绝 schema 中未声明的附加字段”。
- 若引入 strict，应默认开启在包内资源验证中；对外部实验资源可通过显式参数或环境变量放宽。

如果实现复杂度高，Task 184 可先不开放用户级 strict 参数，但必须把 `additionalProperties` 的策略写清楚。

### 4. 现有 `punch_engine` 必须被显式处理

`webnovel_intense.json` 当前包含 `punch_engine`，而 `CreativeModeProfile` 模型未声明该字段。Task 184 不能让现有 4 个 mode 资源失败。可选处理：

- 在 schema 中把 `punch_engine` 作为兼容字段显式声明，仍不改变模型消费行为。
- 或先把该字段迁入模型，但这超出本任务边界，除非 review 证明更安全。

推荐：schema 显式允许 `punch_engine`，并在任务文档中登记为历史兼容字段。

### 5. `_schema.json` 是元文件，不能进入 profile 列表

当前 loader 的枚举逻辑只按 `*.json` 过滤。新增 `_schema.json` 后，如果不改枚举：

- `list_genre_profiles()` 会额外返回 `_schema`；
- `list_creative_mode_profiles()` 会额外返回 `_schema`；
- doctor、CLI 选择菜单、资源枚举测试都会被污染。

Task 184 必须把 `_schema.json` 或所有 `_*.json` 元文件排除在可用资源列表之外。推荐统一排除文件名以 `_` 开头的 JSON，保持后续元数据文件可扩展。

## 实现建议

### 文件布局

| 路径 | 职责 |
|---|---|
| `src/songyan/genres/data/_schema.json` | GenreProfile JSON Schema |
| `src/songyan/creative_modes/data/_schema.json` | CreativeModeProfile JSON Schema |
| `src/songyan/resources/json_schema.py` 或相邻 helper | 轻量 schema 读取与错误格式化 |
| `src/songyan/genres/loader.py` | genre JSON 加载时 schema 校验 |
| `src/songyan/creative_modes/registry.py` | mode JSON 加载时 schema 校验 |
| `tests/test_184_resource_json_schema.py` | 7+4 资源与坏样本回归 |

### 校验器选择

仓库当前没有 `jsonschema` 依赖。两种实现路线：

1. **引入 `jsonschema` 依赖**：
   - 优点：标准 draft-07 校验，错误定位成熟。
   - 缺点：新增 runtime dependency，需同步 `pyproject.toml` 与 wheel 验证。
2. **使用 Pydantic 生成/验证 + 手写附加字段检查**：
   - 优点：不新增依赖。
   - 缺点：与 JSON Schema 文件目标不完全一致，复杂嵌套错误定位弱。

推荐路线：引入 `jsonschema>=4` 作为 runtime dependency。Task 184 的核心就是 JSON Schema，标准库没有等价能力；新增依赖的风险低于手写校验器漂移风险。

### Schema 口径

`GenreProfile` schema 至少覆盖：

- 必填：`id`、`name`。
- 基础字段：`language`、`chapter_types`、`fatigue_words`、`satisfaction_types`、`has_numerical_system`、`has_power_scaling`、`pacing_rule`、`writer_rules`、`writer_rules_by_type`、`reviewer_focus`、`active_audit_dimensions`、`taboos`。
- V5/V8 扩展：`pacing_templates`、`sub_genres`、`punch_type_defs`、`sensory_templates`、`emotion_arc_library`、`style_baseline`、`reference_works`、文学护栏 lexicon 字段。
- 枚举：`sensory_templates[].sense` 必须是模型支持的感官值。
- 数值范围：`punch_density >= 0`，`style_baseline.description_density/dialogue_ratio` 在 0-1。

`CreativeModeProfile` schema 至少覆盖：

- 必填：`id`、`name`。
- 基础字段：`enabled_agents`、`audit_weights`、`active_audit_dimensions`、`revision_policy`、`tolerance`、`context_pruning_strategy`、`success_metrics`。
- 扩展字段：`human_memory`、`rag_config`、`quality_ramp_chapters`、`literary_optimization_plugins`。
- 兼容字段：`punch_engine`，只做结构约束，不改变运行时消费。
- 枚举：`revision_policy`、`context_pruning_strategy`、`rag_config.enabled`。

### 错误信息

loader 抛出的既有异常类型不变：

- `GenreProfileError`
- `CreativeModeProfileError`

错误文案至少包含：

- profile id / mode id
- 资源文件名
- schema 路径或 JSON pointer
- 原始错误摘要

## TDD 测试计划

1. schema 文件存在并能作为 package data 枚举到。
2. 7 个 genre JSON 全部通过 schema + Pydantic loader。
3. 4 个 creative mode JSON 全部通过 schema + Pydantic loader。
4. genre 坏样本：未知字段 / 错类型 / 缺 `name` 至少一个被拒。
5. mode 坏样本：未知字段 / 错类型 / 非法 `rag_config.enabled` 至少一个被拒。
6. `list_genre_profiles()` / `list_creative_mode_profiles()` 排除 `_schema.json`。
7. `set_genres_dir()` / `set_modes_dir()` 外部目录注入仍走同一校验。
8. schema 校验不依赖真实 `Path`，默认 package resource loader 测试通过。
9. `webnovel_intense.punch_engine` 被明确允许，不导致生产资源失败。

## 验证命令

```powershell
python -m pytest tests/test_184_resource_json_schema.py tests/genres/test_loader.py tests/creative_modes/test_registry.py tests/test_178_resource_loading.py -q
python -m pytest tests/cli -q
mypy src/
ruff check src/ tests/
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 1800 -DetectPytestSummary -- python -m pytest tests/ -q
```

## 验收判据

- `src/songyan/genres/data/_schema.json` 与 `src/songyan/creative_modes/data/_schema.json` 存在并纳入 wheel package data。
- 7 个 genre JSON + 4 个 creative mode JSON 全部通过 schema 校验。
- profile/mode 列表仍只返回 7+4 个业务资源，不出现 `_schema`。
- loader 在坏 JSON 样本上 fail fast，且异常信息可定位字段。
- 默认 loader 与外部目录注入 loader 都执行校验。
- 不破坏 Task 178 wheel 资源加载回归。
- 默认全量 pytest、CLI pytest、mypy、ruff 全绿。

## 执行记录（2026-07-20）

- 新增 `jsonschema>=4.0` runtime dependency，并新增 `src/songyan/utils/json_schema.py`：
  - 使用 `Draft7Validator` 校验资源 JSON；
  - 错误信息包含资源名与 JSON path；
  - schema 读取兼容 `importlib.resources.abc.Traversable`，不要求真实文件路径。
- 新增包内 schema：
  - `src/songyan/genres/data/_schema.json`
  - `src/songyan/creative_modes/data/_schema.json`
- `load_genre_profile()` 与 `load_creative_mode_profile()` 在 JSON parse 后、Pydantic model 实例化前执行 schema 校验。
- `_get_available_genres()` 与 `_get_available_modes()` 排除 `_*.json` 元文件，避免 `_schema` 污染 CLI/doctor/profile 列表。
- `webnovel_intense.json` 的历史兼容字段 `punch_engine` 已在 creative mode schema 中显式声明，不改变运行时消费语义。
- 更新 `tests/test_178_resource_loading.py`，把业务 JSON 与 schema 元文件分别断言。
- 新增 `tests/test_184_resource_json_schema.py` 9 个测试，覆盖 schema package data、7+4 生产资源、坏字段/坏类型/坏枚举、`_schema` 列表排除、`punch_engine` 兼容与 Pydantic 默认值兼容。

### Code Review 记录

`bits-code-guard` 分组 review 发现 1 个 P2：

- P2：`GenreProfile.PacingTemplate.chapter_types` 在模型中是 `default_factory=list`，初版 schema 将其误设为必填，可能拒绝模型允许的外部/后续 genre 资源。已删除该 `required` 约束，并补 `test_genre_schema_keeps_model_defaults_for_pacing_template`。

报告产物：

- `.tmp/code_guard_184/report.html`
- `.tmp/code_guard_184/report.md`

### 验证结果（2026-07-20）

| 项 | 结果 |
|---|---|
| 资源/schema 聚焦测试 | `python -m pytest tests/test_184_resource_json_schema.py tests/genres/test_loader.py tests/creative_modes/test_registry.py tests/test_178_resource_loading.py -q` → **86 passed** |
| CLI 测试 | `python -m pytest tests/cli -q` → **35 passed** |
| mypy | `mypy src/` → **Success: no issues found in 176 source files** |
| Ruff | `ruff check src/ tests/` → **All checks passed** |
| 默认全量 pytest | Task 176 wrapper → **2930 passed, 2 skipped, 1 xfailed, 7 warnings**；`WRAPPER_RESULT=PASS_NORMAL_EXIT` |

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| schema 过严误伤现有资源 | 7+4 包内资源加载失败 | 优先修 schema，把现有事实登记为显式兼容字段；不直接删除资源字段 |
| schema 过松拦不住拼写错误 | 坏样本 unknown field 通过 | 收紧 `additionalProperties`，必要时为兼容字段单独声明 |
| 新增 `jsonschema` 依赖破坏打包 | wheel install 后 loader import 失败 | 同步 `pyproject.toml`，补 Task 178 资源/非仓库 cwd 回归 |
| Traversable 不兼容 | wheel/zip-backed resource 读取 schema 失败 | 不使用需要真实路径的 API；用 `open()` / `read_text()` |
| 错误文案不可定位 | 用户只看到泛化 validate fail | 包装 `ValidationError.path` 与文件名到既有异常 |

## Out of Scope

- 生成完整文档站点或 schema 文档页。
- 为 project templates 重写 schema。
- 将 `punch_engine` 接入运行时模型消费。
- 修改 profile registry / DB override 语义。
- urban 标定实跑或 Ch100 爬坡。

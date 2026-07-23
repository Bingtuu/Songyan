# Task 183: Profile 调参 CLI

> **阶段**: V9.3 爬坡工具链
> **类型**: CLI / 调参工具 / GenreRuntimeProfile DB 覆盖层
> **优先级**: P1（V9 A8：标定迭代全程不改代码）
> **依赖**: 172i/172j 覆盖语义已固化；182 五门工具已完成；173-181 生产化地基已完成
> **状态**: ✅ 完成（DONE: `archive/v9/183-profile-tuning-cli-DONE.md`）
> **来源**: `tasks/V9-README.md` Task 183 行；V9 A8 判据

---

## 任务边界

本任务为 `GenreRuntimeProfile` 增加正式调参 CLI：

1. `songyan profile show --genre <g>`：展示注册表基线、DB 显式覆盖、生效值。
2. `songyan profile diff --genre <g>`：展示 DB 覆盖相对注册表基线造成的生效差异。
3. `songyan profile upsert --genre <g>`：写入 DB 覆盖层，使标定迭代不改代码。

不做：

- 不改变 `load_profile()` 的覆盖语义。
- 不改 `genre_runtime_profiles` 表结构；不做稀疏覆盖存储迁移。
- 不新增 Agent / Workflow 节点。
- 不做 urban 标定实跑；那是 Task 185。
- 不实现 JSON Schema；那是 Task 184。

## 当前事实

- `GenreRuntimeProfileRepository` 已有 `get()` / `upsert()` / `list_all()`。
- `load_profile()` 的 172i/172j 最终语义：
  - 代码注册表是体裁基线。
  - DB 记录是字段级覆盖层。
  - DB 覆盖判定以 `GenreRuntimeProfile(genre=<g>)` 这个“全新代码默认模型”为 diff 基准。
  - 嵌套子模型按整体替换，不细粒度合并内部键。
  - DB 存全量 `profile_json`，因此无法表达“把注册表调优值降回代码默认”；如需降回，修改代码注册表或未来改稀疏覆盖存储。
- 172j 已固化 `max_*` 语义：`max_soft_refs` / `max_foreshadowing` / `max_character_states` 只作为体裁级收紧上限，调低到旧常量以下才生效，调高由章节动态曲线接管。

## 关键设计约束

### 1. upsert 不能写“生效 profile 全量值”

如果 CLI 把 `load_profile("xuanhuan")` 的生效全量值直接写入 DB，`load_profile()` 后续会把注册表调优值（如 xuanhuan `base_budget=15000`、`foreshadowing_horizon_floor=48`）误判为 DB 显式覆盖，破坏“DB 只存用户调参意图”的可解释性。

因此 Task 183 的 upsert 必须构造：

```text
db_profile_json = GenreRuntimeProfile(genre=<g>)  # 全新代码默认模型
                  + 用户显式设置的字段
```

这样现有 `load_profile()` 的 diff 语义才能把“用户显式字段”合并到注册表基线上。

### 2. 嵌套子模型整体替换要直接暴露

例如：

```powershell
songyan profile upsert --genre wuxia --set continuity.health_overdue_weight=0.2
```

DB 中的 `continuity` 子模型会整体异于默认值，因此 `load_profile()` 会用 DB `continuity` 整体替换注册表 `continuity`。CLI 必须在 `show/diff` 中把该行为显式展示，避免用户误以为只是内部字段细粒度合并。

### 3. reset 能清空 DB 覆盖意图

由于不做 delete 子命令，本任务允许：

```powershell
songyan profile upsert --genre <g> --reset
```

它写入 `GenreRuntimeProfile(genre=<g>)` 的默认模型，使 DB diff 为空；生效值回到注册表基线。该行为用于撤销 DB 覆盖，不删除行也不改 schema。

## CLI 方案

### 1. `show`

```powershell
songyan profile show --genre xuanhuan
songyan profile show --genre xuanhuan --json
```

输出三列：

| field | registry | db_override | effective |
|---|---|---|---|
| `base_budget` | `15000` | `-` | `15000` |
| `foreshadowing_horizon_floor` | `48` | `-` | `48` |
| `continuity.health_overdue_weight` | `0.3` | `0.2` | `0.2` |

说明：

- `registry`：`load_profile_from_registry(genre)`。
- `db_override`：DB profile 相对 `GenreRuntimeProfile(genre=<g>)` 的显式 diff；无 diff 显示 `-`。
- `effective`：`await load_profile(genre)`。
- `--json` 输出机器可读结构，便于标定脚本和回归测试。

### 2. `diff`

```powershell
songyan profile diff --genre wuxia
songyan profile diff --genre wuxia --json
```

输出 DB 覆盖导致的生效差异：

- `registry_value`
- `effective_value`
- `db_override_value`
- `source`: `registry` / `db_override`

`diff` 只展示有效差异，不列全表。若无 DB 覆盖差异，输出“无 DB override；effective == registry”。

### 3. `upsert`

```powershell
songyan profile upsert --genre urban --set base_budget=12000
songyan profile upsert --genre urban --set base_budget=13000 --set foreshadowing_horizon_floor=48
songyan profile upsert --genre wuxia --set continuity.health_overdue_weight=0.2
songyan profile upsert --genre urban --from-json .tmp/urban-profile-overrides.json
songyan profile upsert --genre urban --reset
```

约束：

- `--set key=value` 支持顶层字段和一层嵌套字段（如 `continuity.health_overdue_weight`）。
- `value` 先按 JSON scalar/object 解析（数字、布尔、对象），解析失败再作为字符串；写入前由 Pydantic 做最终类型校验。
- `--from-json` 接收“覆盖意图 JSON”，不是生效 profile 全量 JSON。
- `--set` 与 `--from-json` 可合并；同字段重复必须 fail fast，避免 argparse 顺序语义不清。
- `--reset` 与 `--set` / `--from-json` 互斥。
- `upsert` 仅允许注册表已知体裁；未知体裁当前会被 `load_profile()` 回退 scifi baseline，DB override 不能可靠生效，因此本任务不开放。
- 写入前用 Pydantic 校验完整 `GenreRuntimeProfile`，非法字段/非法类型 fail fast。
- 写入后回读 `load_profile()` 并显示生效摘要。

## 实现建议

新增 service 层，避免把 JSON diff/渲染逻辑塞进 `cli/main.py`：

| 路径 | 职责 |
|---|---|
| `src/songyan/services/profile_service.py` | diff 计算、override profile 构造、三列数据结构、upsert 调用 |
| `src/songyan/cli/main.py` | 注册 `profile` group 与 show/diff/upsert command，调用 service |
| `tests/cli/test_profile_command.py` 或 `tests/test_183_profile_cli.py` | 聚焦 CLI/service 测试 |

核心 helper：

- `flatten_profile(profile) -> dict[str, Any]`：把 Pydantic 模型扁平化为 dot path。
- `explicit_override_diff(db_profile) -> dict[str, Any]`：DB profile 与 `GenreRuntimeProfile(genre=g)` 比较。
- `build_db_override_profile(genre, overrides) -> GenreRuntimeProfile`：从默认模型叠加用户显式字段。
- `profile_triplet(genre) -> registry/db/effective`：为 show/diff 提供三列数据。

初始化/只读约束：

- `show` / `diff` 是只读命令，不主动调用 `init_schema()`；DB 不可用时仍能展示 registry，并把 DB override 标为 unavailable/none。
- `upsert` 是写命令，允许先调用 `init_schema()` 确保 `genre_runtime_profiles` 表存在。

## TDD 测试计划

1. `show` 无 DB 覆盖：
   - registry xuanhuan `base_budget=15000`；
   - `db_override` 为空；
   - effective = registry。
2. `upsert --set base_budget=12000`：
   - DB row 存在；
   - `load_profile("urban").base_budget == 12000`；
   - show/diff 显示 `base_budget` 来自 DB override。
3. upsert 不写生效全量值：
   - 对 xuanhuan 只 `--set ramp_per_chapter=300`；
   - DB profile JSON 中 `base_budget` 应仍为代码默认 8000，不应把 registry 15000 写成 DB 显式覆盖；
   - `load_profile("xuanhuan").base_budget` 仍为 registry 15000，`ramp_per_chapter` 为 300。
4. 嵌套子模型整体替换：
   - `--set continuity.health_overdue_weight=0.2` 后，show/diff 标注 `continuity` 为 DB override；
   - 文案提示 nested replacement。
5. `--reset`：
   - 写入默认模型；
   - DB diff 为空；
   - effective 回到 registry baseline。
6. 错误输入：
   - unknown field fail；
   - wrong type fail；
   - `--reset` 与 `--set` 同时出现 fail。
   - unknown genre upsert fail。
7. `show/diff` 不调用 `init_schema()`；`upsert` 会初始化 schema 并写入。
8. CLI JSON 输出可解析，不被日志污染。

## 验证命令

```powershell
python -m pytest tests/test_183_profile_cli.py -q
python -m pytest tests/cli -q
mypy src/
ruff check src/ tests/
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 1800 -DetectPytestSummary -- python -m pytest tests/ -q
```

可选本地验收：

```powershell
songyan profile show --genre urban --json
songyan profile upsert --genre urban --set base_budget=12000
songyan profile diff --genre urban
songyan profile upsert --genre urban --reset
```

## 验收判据

- `songyan profile show/diff/upsert --genre <g>` 可用。
- 一次 DB 覆盖调参全程不改代码完成。
- show/diff 明确展示注册表基线 / DB 显式覆盖 / 生效值。
- upsert 不把注册表调优值误写成 DB 显式覆盖。
- `--reset` 能撤销 DB 覆盖意图。
- 默认全量 pytest、CLI pytest、mypy、ruff 全绿。

## 执行记录（2026-07-20）

- 新增 `src/songyan/services/profile_service.py`：
  - `show/diff` 使用 sqlite3 URI read-only 读取 DB override，不调用 `init_schema()`，不会创建空 DB；
  - `upsert` 构造 `GenreRuntimeProfile(genre=<g>) + 用户显式字段` 的 DB profile，避免把 registry 生效全量误写成 DB override；
  - 支持 `--set key=value`、`--from-json`、`--reset`；
  - 嵌套字段递归校验，非法字段 fail fast，不被 Pydantic `extra=ignore` 吞掉；
  - show/diff 三列输出 registry / db_override / effective，并标注 nested replacement。
- `src/songyan/cli/main.py` 新增 `songyan profile show/diff/upsert`。
- 新增 `tests/test_183_profile_cli.py` 7 个测试：
  - show JSON 不创建缺失 DB；
  - upsert 只写默认模型 + 显式 override；
  - nested replacement 可见；
  - reset 清空 DB override 意图；
  - unknown genre、重复字段、未知嵌套字段 fail fast。

### Code Review 记录

`bits-code-guard` / 本地 fallback review 发现 1 个 P2：

- P2：`continuity.typo=...` 这类非法嵌套字段会被折成顶层 dict 后交给 Pydantic，可能因 `extra=ignore` 被默默吞掉。已修复为 `_assign_model_parts()` 递归校验，并补 `test_profile_upsert_rejects_unknown_nested_field`。

报告产物：

- `.tmp/code_guard_183/report.html`
- `.tmp/code_guard_183/report.md`

### 验证结果（2026-07-20）

| 项 | 结果 |
|---|---|
| 聚焦测试 | `python -m pytest tests/test_183_profile_cli.py -q` → **7 passed** |
| CLI 测试 | `python -m pytest tests/cli -q` → **35 passed** |
| mypy | `mypy src/` → **Success: no issues found in 175 source files** |
| Ruff | `ruff check src/ tests/` → **All checks passed** |
| 默认全量 pytest | Task 176 wrapper → **2921 passed, 2 skipped, 1 xfailed, 7 warnings**；`WRAPPER_RESULT=PASS_NORMAL_EXIT` |

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| upsert 误写生效全量 profile | DB diff 中出现用户未设置的注册表调优字段 | 改为从 `GenreRuntimeProfile(genre=g)` 叠加 overrides，补回归测试 |
| 嵌套字段用户预期细粒度合并 | show/diff 与 effective 不一致或误导 | 在 CLI 输出 nested replacement 提示；必要时拒绝嵌套 dot-path，只允许完整子模型 JSON |
| JSON 输出被日志污染 | `--json` 结果无法 `json.loads()` | 参考 Task 180 doctor 处理，确保 command 输出仅 JSON |
| reset 语义不清 | DB row 存在但 diff 为空，用户误以为仍覆盖 | show/diff 明确显示 `db_override: none`，并说明 effective 来自 registry |
| 未知体裁 upsert 失效 | DB 写入后 `load_profile()` 仍回退 scifi | 本任务 upsert 拒绝未知体裁；未知体裁 Profile 支持需另行调整 `load_profile()` 语义 |

## Out of Scope

- 删除 DB profile row 的独立命令。
- 稀疏覆盖存储 schema 迁移。
- profile schema 生成或 JSON Schema 校验。
- urban 真实标定实跑。

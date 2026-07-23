# Task 138d: 修复后 Ch10-Ch12 聚焦复跑验证

> **类型**: 实跑验证
> **状态**: 已完成
> **前置**: Task 138c

## 背景

Task 138c 完成最小修复后，需要用与 `run-4ba8de9d` 同口径的 Ch10-Ch12 聚焦复跑验证修复效果。复跑必须使用副本 DB，不能污染主库。

## 基线

- Run ID: `run-4ba8de9d`
- DB: `.tmp/task137_ch10_focus_20260628_183255.db`
- Ch12 accepted: `v-12-6-75a4b0c7`
- Ch12 continuity: `health=3.0`、`orphaned=19`、`forgotten=2`、`mismatches=0`

## 待办

- [x] 创建新的 `.tmp` 副本 DB，清理 Ch11+ 残留，保留 Ch1-Ch10 accepted 锚点。
- [x] 执行 `scripts/run_137_ch10_focus_validation.py`。
- [x] 记录 run id、heads、run log、Writer manifest 恢复状态。
- [x] 验证 Ch11/Ch12 settlement、summary、quality gate 均通过。
- [x] 确认 run log 没有新的 `settlement_validation_errors`。
- [x] 读取 Ch12 continuity，并与 `run-4ba8de9d` 比较。

## 验收

- 副本 DB 未污染主库。
- Ch10-Ch12 completed。
- Ch12 orphan 继续下降，且 health 脱离或接近脱离 3.0。
- 若仍失败，回到 Task 138a 分类新证据。

## 结果

- Run ID: `run-4fd48756`
- DB: `.tmp/task138d_ch10_focus_20260628_201716.db`
- project_runs: `status=completed`、`current_chapter=12`、`completed_chapters=[10, 11, 12]`、`failed_chapters=[]`
- Heads: Ch10 `v-10-6-4c80f8c7` accepted；Ch11 `rev-11-3-a31b2add` accepted；Ch12 `v-12-3-a240b75d` accepted。
- Run log: Ch11/Ch12 均 `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`settlement_validation_errors=[]`。
- Writer manifest: 运行结束后已恢复为 `default_version: "1.1.0"`。
- Ch12 continuity 对比 baseline:

| 指标 | Baseline `run-4ba8de9d` | Task 138d `run-4fd48756` | 变化 |
|------|--------------------------|---------------------------|------|
| health | 3.0 | 3.0 | 持平 |
| orphaned | 19 | 16 | -3 |
| forgotten | 2 | 2 | 持平 |
| mismatches | 0 | 0 | 持平 |

结论: Task 138c 的局部修复在同口径 Ch10-Ch12 副本 DB 复跑中生效，Ch12 orphan 从 19 降至 16；health 仍为 3.0，未脱离低分区间。下一步进入 Task 138e 同步事实源，并决定是归档 Task 137 还是基于 `run-4fd48756` 的 16 个 orphan 进入下一轮分类。

---

## Round 2 / Task 138d-R2

> **状态**: 中断，未完成验证
> **前置**: Task 138c-R2

### 目标

使用新的副本 DB 复跑 Ch10-Ch12，验证 Ch12 orphan 是否低于 `run-4fd48756` baseline `orphaned=16`，并确认 health 是否脱离 `3.0`。

### 运行证据

- Run ID: `run-dcd56146`
- DB: `.tmp/task138d_r2_ch10_focus_20260628_212511.db`
- 运行方式: `scripts/run_137_ch10_focus_validation.py`
- Writer manifest: 体检时已恢复为 `default_version: "1.1.0"`
- 进程状态: 原 wrapper PID `39628` 与 python PID `29624` 已不存在。

### 中断状态

- `project_runs.status`: `running`
- `current_chapter`: 11
- `completed_chapters`: `[]`
- `failed_chapters`: `[]`
- Ch10 head: accepted `v-10-6-4c80f8c7`
- Ch11 head: draft `v-11-3-ede691d6`，`accepted_version_id=None`
- Ch12: 未进入本轮新 head；仍只能看到旧 accepted head
- run log: `logs/chapter_runs/run-dcd56146.jsonl` 未生成
- DB mtime: `2026-06-28 21:34:11`

### 结论

本轮未完成 Ch11，更未进入 Ch12；因此无法验证 Ch12 orphan 是否低于 baseline 16，也无法生成新的 Ch12 continuity。该结果不是业务失败证据，而是运行中断/进程消失证据。

### 下一步

- 不创建 Task 138e-R2。
- 不归档 Task 137。
- 先定位 `run-dcd56146` 为何在 Ch11 draft 阶段中断且无 run log。
- 定位后再决定重新发起受控 Ch10-Ch12 复跑，或补充新的运行防卡/日志持久化任务。

---

## Round 2 Blocker / run-5054ac69

> **状态**: 已定位并最小修复；Task 138d-R2 仍未完成验证

### 失败证据

- Run ID: `run-5054ac69`
- DB: `.tmp/task138d_r2_ch10_focus_20260628_212448.db`
- Ch12 version: `v-12-3-b76b6b4f`
- Ch12 状态: `draft`，`accepted_version_id=None`
- Run log: Ch12 `success=false`、`error_stage=settlement_review`、`settlement_success=false`、`quality_gate_passed=true`
- validation error: `角色 lin_shen 的 left_leg_prosthetic_temperature closing_value (50.6) 不等于 公式值 (52.000)`
- 正文证据: `左腿义肢的温度继续下降。52.0，51.3，50.6。`

### 根因

- `left_leg_prosthetic_temperature` 已命中 telemetry attribute。
- `_extract_temperature_readings()` 原规则只识别 `52.3度` / `四十七点三度` 这类带“度”的温度读数。
- Ch12 的最终读数序列写作 `温度继续下降。52.0，51.3，50.6。`，数字不带单位，导致 `_normalize_telemetry_snapshot()` 未规整为 `telemetry_snapshot`。
- validation 随后按真实 numerical ledger 执行 `opening + increments - decrements == closing`，得到公式值 `52.000`，触发阻断。

### 最小修复

- `src/songyan/agents/settlement_extractor/_validate.py`
  - 温度提取规则最小扩展为：在明确温度关键词后的短窗口内，允许提取无单位小数序列。
  - 证据来源仍只来自正文 content 或 increment/decrement `source_quote`，不使用 `formula` 自证。
  - 未放宽真实资源、库存、数量类 numerical ledger 的公式硬校验。
- `tests/test_settlement_extractor.py`
  - 新增 `50.6` 与 `52.0` 温度小数读数 snapshot 回归。
  - 新增无正文/source_quote 明确读数仍失败的负例。
  - 新增真实资源数值公式错误仍失败的负例。

### 验证

- `python -m pytest tests/test_settlement_extractor.py -q`
  - 结果: `103 passed, 1 xfailed in 27.21s`
- `ruff check src/songyan/agents/settlement_extractor/_validate.py tests/test_settlement_extractor.py`
  - 结果: `All checks passed!`

### 下一步

- 可以重新发起新的 Task 138d-R2 retry，仍使用副本 DB，复跑 Ch10-Ch12。
- 本次未执行 Ch10-Ch12 复跑，因此仍不能创建 Task 138e-R2，也不能归档 Task 137。

---

## Round 2 Retry / run-1155c92a 与 run-9f87da6f

> **状态**: 未完成验证；两次 retry 均停在 Ch11 `settlement_review`

### 已执行的 retry

| Run ID | DB | 结果 | validation errors |
|--------|----|------|-------------------|
| `run-1155c92a` | `.tmp/task138d_r2_retry_ch10_focus_20260628_221500.db` | `partial`，Ch11 draft `v-11-5-e116d0be`，未进入 Ch12 | `neural_pattern_match_rate` 两项、`beacon_core_countdown` 一项 |
| `run-9f87da6f` | `.tmp/task138d_r2_retry2_ch10_focus_20260628_222000.db` | `partial`，Ch11 draft `v-11-6-f0aea93b`，未进入 Ch12 | `consciousness_upload_progress closing_value (60.0) != 公式值 (33.300)` |

### 中间修复

- 已补 `neural_pattern_match_rate` 的明确百分比读数 snapshot 规则。
- 已补 `47小时21分03秒` 这类中文小时/分钟/秒倒计时换算秒规则。
- 验证: `python -m pytest tests/test_settlement_extractor.py -q` -> `106 passed, 1 xfailed in 28.71s`。
- 验证: `ruff check src/songyan/agents/settlement_extractor/_validate.py tests/test_settlement_extractor.py` -> `All checks passed!`。

### 当前结论

- `run-9f87da6f` 未生成 Ch12 accepted head，也未生成 Ch12 continuity report。
- 因此本轮无法验证 Ch12 `orphaned < 16`，也不能进入 Task 138e-R2。
- Writer manifest 已恢复为 `default_version: "1.1.0"`。
- 最新阻断不应被静默吞掉：`consciousness_upload_progress=60.0` 在 Ch11 正文未找到明确 `60%/60.0` 读数证据，不能放宽为无证据 telemetry snapshot。

### 下一步

- 不创建 Task 138e-R2。
- 不归档 Task 137。
- 先针对 `run-9f87da6f` 的 `consciousness_upload_progress` 进入新的最小定位/决策步骤；若确认 LLM 输出无正文证据，应修 prompt/提取约束或分类为 settlement 输出错误，而不是继续扩大 telemetry 规则。

---

## Plan Adjustment / consciousness_upload_progress 优先级提升

> **状态**: 当前最高优先级，阻止继续复跑

### 调整原因

- `run-9f87da6f` 是当前最新 retry，已证明前序温度、匹配度、中文倒计时 telemetry 缺口不再是当前首要阻断。
- 最新失败停在 Ch11 `settlement_review`，字段为 `consciousness_upload_progress`。
- 当前只查到正文存在“意识上传协议”等概念描述，尚未找到明确 `60%` / `60.0` 读数证据。
- 因此不能继续扩展 telemetry snapshot 规则来吞掉该错误；否则会破坏 `numerical_update.closing_value == formula` 的硬约束。

### 新优先级顺序

| 顺序 | 工作项 | 目标 | 退出条件 |
|------|--------|------|----------|
| 1 | `consciousness_upload_progress` 证据定位 | 查询 Ch11 `v-11-6-f0aea93b` 正文、source_quote、settlement payload、run log | 明确是否存在 `60%/60.0` 读数证据 |
| 2 | 决策最小修复方向 | 无证据则修 prompt/解析约束或输出过滤；有证据才补 telemetry evidence 规则 | 不允许无证据 snapshot |
| 3 | 目标测试 | 覆盖正例/负例，尤其是无证据 progress 仍失败 | `pytest` 目标测试 + `ruff check src/ tests/` 通过 |
| 4 | 新副本 DB 复跑 | 重新运行 Ch10-Ch12 | 进入 Ch12 continuity 并比较 `orphaned < 16` |

### 当前非目标

- 不进入 Task 138e-R2。
- 不归档 Task 137。
- 不直接扩大到 Ch1-Ch20/default run。
- 不为 `consciousness_upload_progress` 增加无证据 telemetry 白名单。

---

## Task 138f 完成后状态

> **状态**: `consciousness_upload_progress` 阻断已通过 evidence gate 工程化处理

- Task 138f 已完成 Settlement numerical_update evidence gate。
- `run-9f87da6f` / Ch11 `v-11-6-f0aea93b` 证据结论:
  - 正文有“进度条”“大约三分之一”等概念性或图形化描述。
  - 正文没有明确 `60.0`、`60%`、`60％`、`六十`、`百分之六十` 读数证据。
  - 因此 `consciousness_upload_progress=60.0` 属于无证据 telemetry 候选。
- 工程处理:
  - 有明确读数证据的 telemetry snapshot 仍可规整。
  - 无明确读数证据且公式不闭合的 telemetry numerical_update 会过滤并记录 diagnostic。
  - 真实 ledger 公式错误继续硬失败。
- 验证:
  - `python -m pytest tests/test_settlement_extractor.py -q` -> `111 passed, 1 xfailed in 18.83s`。
  - `ruff check src/songyan/agents/settlement_extractor/_validate.py tests/test_settlement_extractor.py` -> `All checks passed!`。
  - `ruff check src/ tests/` -> `All checks passed!`。
  - `python -m pytest tests/ -q` -> `1973 passed, 1 xfailed, 2 warnings in 299.26s`。

### 下一步

- 可以重新发起新的 Task 138d-R2 Ch10-Ch12 副本 DB retry。
- retry 仍必须使用新的 `.tmp` DB 副本，不污染主库。
- 验收仍是：Ch11/Ch12 settlement、summary、QG 通过，Ch12 continuity 生成，并验证 `orphaned < 16`。

---

## Round 2 Retry 3 / run-0a48030b

> **状态**: 未完成验证；Ch11 已通过，Ch12 停在 `settlement_review`

### 运行证据

- Run ID: `run-0a48030b`
- DB: `.tmp/task138d_r2_retry3_ch10_focus_20260628_231943.db`
- 运行方式: `scripts/run_137_ch10_focus_validation.py`
- Writer manifest: 运行后已恢复为 `default_version: "1.1.0"`
- 残留进程: run 报告生成后 wrapper/python 未自行退出，已按 PID 清理，仅限本次验证进程。

### 结果

- `project_runs.status`: `partial`
- `current_chapter`: 12
- `completed_chapters`: `[10, 11]`
- `failed_chapters`: `[12]`
- Ch10 head: accepted `v-10-6-4c80f8c7`
- Ch11 head: accepted `rev-11-2-48be5b05`
- Ch12 head: draft `v-12-3-8e4001b7`，`accepted_version_id=None`
- Ch12 continuity: 未生成，因此无法比较 `orphaned < 16`。

### Run log

- Ch11: `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`settlement_validation_errors=[]`。
- Ch12: `success=false`、`error_stage=settlement_review`、`settlement_success=false`、`summary_success=false`、`quality_gate_passed=true`。

### Ch12 validation errors

- `channel_wall_contraction_period closing_value (1.7) != 公式值 (2.000)`
- `channel_wall_relaxation_period closing_value (1.1) != 公式值 (1.300)`
- `knife_sheath_spring_tension_decay closing_value (12.0) != 公式值 (0.000)`
- `vertical_pipe_depth closing_value (20.0) != 公式值 (0.000)`
- `liquid_metal_tentacle_distance closing_value (8.0) != 公式值 (0.000)`

### 初步定位

这次不再是 `consciousness_upload_progress` 无证据读数回归；Task 138f 的 evidence gate 已帮助 Ch11 越过之前阻断。Ch12 新失败集中在环境/结构读数类属性，正文存在明确读数证据：

- `收缩周期：1.7秒。`
- `舒张周期：1.1秒。`
- `刀鞘卡扣的弹簧张力衰减了12%。`
- `通道底部有微弱的蓝光，距离大约二十米。`
- `银白色液态金属的距离：大约八米。`

根因倾向: 这些属性名未命中当前 telemetry/evidence gate 的属性关键词或 alias 规则，因此没有被规整为 evidence-backed snapshot，而是继续走 numerical ledger 公式硬校验。

### 下一步

- 不创建 Task 138e-R2。
- 不归档 Task 137。
- 进入新的最小定位/修复步骤：扩展 evidence-backed snapshot 的属性分类与 alias 规则，但必须采用严格 allowlist，不允许把所有公式不闭合的 `numerical_update` 泛化降级为 snapshot。
- allowlist 仅覆盖本轮已出现且有正文明确读数证据的环境/结构读数字段类别：
  - `period` / `周期`：如 `channel_wall_contraction_period`、`channel_wall_relaxation_period`，证据需包含明确秒数读数。
  - `decay` / `衰减`：如 `knife_sheath_spring_tension_decay`，证据需包含明确百分比或数值读数。
  - `depth` / `深度`、`distance` / `距离`：如 `vertical_pipe_depth`、`liquid_metal_tentacle_distance`，证据需包含明确距离读数。
- 测试要求必须同时覆盖正例和负例：
  - 正例：`收缩周期：1.7秒`、`舒张周期：1.1秒`、`衰减了12%`、`距离大约二十米`、`距离：大约八米` 可规整为 evidence-backed snapshot。
  - 负例：无正文 content 或 source_quote 明确读数时仍过滤或失败；真实 ledger 公式错误仍保持硬失败。
- 复跑出口条件不能只看 Ch12 settlement 通过；必须使用新的 `.tmp` 副本 DB 复跑 Ch10-Ch12，并满足 Ch11/Ch12 settlement、summary、QG 全部通过，Ch12 continuity 成功生成，再比较 `orphaned < 16`。
- 若 Ch12 continuity 生成但 `orphaned >= 16` 或 health 仍无法改善，则本次修复只能判定为 settlement 阻断解除，Task 137 仍不能收口，需继续基于新的 continuity 证据分类。

### 最小修复实现

- `src/songyan/agents/settlement_extractor/_validate.py`
  - 在 telemetry attribute allowlist 中新增 `period`/`周期`、`decay`/`衰减`、`depth`/`深度`、`distance`/`距离`。
  - 在 alias 组中仅为本轮环境/结构读数补充有限别名：`收缩周期`、`舒张周期`、`张力衰减`、`弹簧张力衰减`、`深度`、`距离`。
  - 仍复用 Task 138f evidence gate：有明确正文/source_quote 读数才规整为 `telemetry_snapshot`；无证据候选过滤；真实 ledger 继续执行公式硬校验。
- `tests/test_settlement_extractor.py`
  - 新增 Ch12 retry3 五个正例：`channel_wall_contraction_period`、`channel_wall_relaxation_period`、`knife_sheath_spring_tension_decay`、`vertical_pipe_depth`、`liquid_metal_tentacle_distance`。
  - 新增 allowlist 字段无明确读数时仍过滤的负例。
  - 既有真实 ledger 公式错误负例继续覆盖未放宽台账硬校验。

### 本地验证

- `python -m pytest tests/test_settlement_extractor.py -q` -> `117 passed, 1 xfailed`
- `ruff check src/songyan/agents/settlement_extractor/_validate.py tests/test_settlement_extractor.py` -> `All checks passed!`
- `python -m pytest tests/ -q` -> `1979 passed, 1 xfailed, 2 warnings`
- `ruff check src/ tests/` -> `All checks passed!`

### 待复跑

- 仍不能创建 Task 138e-R2。
- 仍不能归档 Task 137。
- 下一步必须使用新的 `.tmp` 副本 DB 复跑 Ch10-Ch12；只有 Ch12 continuity 生成后，才能比较 `orphaned < 16` 并判断 Task 137 是否有收口条件。

---

## Round 2 Retry 4 / run-bcee6ab6

> **状态**: 已完成验证；Ch11/Ch12 settlement、summary、QG 全部通过，Ch12 continuity 已生成

### 运行证据

- Run ID: `run-bcee6ab6`
- DB: `.tmp/task138d_r2_retry4_ch10_focus_20260629_101459.db`
- 运行方式: `scripts/run_137_ch10_focus_validation.py`
- Report: `archive/v5/reports/task-137-ch10-focus-validation-report.md`
- Writer manifest: 运行后已恢复为 `default_version: "1.1.0"`。
- 进程清理: 报告生成后存在短暂 wrapper/python 残留；复查时已无该验证进程。

### 结果

- `project_runs.status`: `completed`
- `current_chapter`: 12
- `completed_chapters`: `[10, 11, 12]`
- `failed_chapters`: `[]`
- Ch10 head: accepted `v-10-6-4c80f8c7`
- Ch11 head: accepted `v-11-4-ded05cbb`
- Ch12 head: accepted `v-12-1-69152a68`

### Run log

- Ch11: `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`settlement_validation_errors=[]`。
- Ch12: `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`settlement_validation_errors=[]`。

### Ch12 continuity 对比

| 指标 | Baseline `run-4fd48756` | Retry4 `run-bcee6ab6` | 变化 |
|------|--------------------------|------------------------|------|
| health | 3.0 | 3.0 | 持平 |
| orphaned | 16 | 14 | -2 |
| mismatches | 0 | 0 | 持平 |

### 结论

- Task 138d-R2 retry3 暴露的环境/结构读数类 `settlement_review` 阻断已解除。
- Ch12 continuity 已生成，`orphaned=14`，低于 baseline 16。
- Health 仍为 3.0，说明本轮只能证明 settlement 阻断解除和 orphan 继续下降，不能直接归档 Task 137。
- 下一步进入 Task 137 事实同步与收口判断：基于 Ch12 continuity `health=3.0`、`orphaned=14` 判断是否需要继续分类剩余 orphan，或是否可接受为当前阶段收口口径。

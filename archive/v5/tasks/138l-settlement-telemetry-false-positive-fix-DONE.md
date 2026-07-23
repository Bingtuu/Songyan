> **ID**: 138l
> **类型**: Bugfix / 结算验证
> **状态**: 已完成
> **前置**: Task 138k Ch1-Ch30 rehearsal 在 Ch10 因 settlement validation 失败中断

# Task 138l: Settlement 数值遥测误报修复

## 问题现象

Task 138k 长窗口 rehearsal（`run-6a0640d4`）在 **Ch10 settlement 阶段失败**，未触发 AutoHalt，但 run 状态变为 `partial`，无法继续生成 Ch11+：

```text
角色 char_lin_shen 的 external_signal_pulse_width_ms closing_value (2.7) 不等于 公式值 (0.000)
角色 char_lin_shen 的 external_signal_transmission_count closing_value (6.0) 不等于 公式值 (0.000)
角色 char_lin_shen 的 coordinate_error_arcseconds closing_value (0.0003) 不等于 公式值 (0.000)
```

同类问题在 Ch10 初稿（`v-10-1-f388cd37`）也出现在：

```text
角色 lin_shen 的 format_conversion_node_response_latency closing_value (11.3) 不等于 公式值 (2.400)
```

## 根因分析

`src/songyan/agents/settlement_extractor/_validate.py` 中的 `_is_telemetry_attribute` 只覆盖了一批硬编码读数型关键词（`temperature`、`frequency`、`pressure`、`countdown` 等）。

当 SettlementExtractor 从科幻文本中提取出以下快照型属性时：

- `external_signal_pulse_width_ms`
- `external_signal_transmission_count`
- `coordinate_error_arcseconds`
- `format_conversion_node_response_latency`

这些属性名**不在** telemetry 关键词/别名列表中，因此被当成普通台账（ledger）字段硬校验：

```python
expected = opening_value + sum(increments) - sum(decrements)
```

由于它们是首次出现的遥测快照，`opening_value=0`、`increments=[]`、`decrements=[]`，而 `closing_value` 是正文中的实测值，自然导致 `closing_value != expected` 的误报。

日志中也验证了这一点：

- 部分属性（如 `external_signal_frequency`、`time_gap_seconds`）因 `_should_filter_unevidenced_numerical_update` 被识别为 telemetry 并过滤；
- 另一部分属性因 `_is_telemetry_attribute` 返回 `False`，未被过滤，进入硬校验后报错。

## 修复目标

让 settlement 验证正确识别“遥测快照型”数值更新，不再对以下属性误报公式不匹配：

- 信号/脉冲类：`signal_*`、`pulse_*`、`transmission_*`
- 延迟/坐标/误差类：`*_latency`、`*_error`、`*_arcseconds`
- 显式声明 `formula == "telemetry snapshot"` 的数值更新（兜底）

同时保持对真实台账字段（如 `cultivation_level`、`hit_points`、`experience_points`）的硬校验不变。

## 复现证据

- 副本 DB：`.tmp/task138k_ch1_ch30_rehearsal_20260629.db`
- 验证项目：`3bef1af8d54d4d0e887658516e1ed350`
- Run ID：`run-6a0640d4`
- 失败版本：`rev-10-4-6988af8e`
- Run log：`logs/chapter_runs/run-6a0640d4.jsonl`（Ch10）
- 报告：`archive/v5/reports/task-138k-long-window-rehearsal-report.md`

## 修复方案

### 方案 A：扩展 telemetry 关键词 + 公式兜底（推荐）

修改 `src/songyan/agents/settlement_extractor/_validate.py`：

1. 在 `_is_telemetry_attribute` 中新增关键词/别名组：
   - `pulse_width`、`transmission_count`、`signal_*`
   - `latency`、`response_time`、`delay`
   - `coordinate`、`arcseconds`、`error`、`deviation`
2. 在 `_normalize_telemetry_snapshot` 和 `_should_filter_unevidenced_numerical_update` 中增加公式兜底：
   - 若 `num.formula.strip().lower() == "telemetry snapshot"`，即使属性名未命中关键词，也按 telemetry 处理。

### 方案 B：放宽无证据过滤条件

对任意 `opening_value == 0` 且无 `increments/decrements` 的数值更新，只要正文中有明确数字证据（任意数字上下文），就按快照处理。风险：可能放过真正的 ledger 错误。

**暂不采用方案 B**，因为会削弱 Task 138f 引入的数值证据门禁。

## 验收标准

- [x] `pytest tests/test_settlement_extractor.py -q` 通过。
- [x] 新增单元测试覆盖 `external_signal_pulse_width_ms`、`transmission_count`、`coordinate_error_arcseconds`、`format_conversion_node_response_latency` 四个场景：
  - 正文无相关数字 → 被过滤，不报错；
  - 正文有相关数字 → 被归一化为 `telemetry_snapshot`，不报错。
- [x] 使用同一副本 DB 重新执行 Ch10 settlement 验证，不再出现上述 3 个 numerical formula 错误。
- [x] 修复后重启 Task 138k，Ch10 成功通过并继续生成 Ch11+。

## 实施记录

- **2026-06-29**: 定位根因并实施修复。
  - 修改文件：`src/songyan/agents/settlement_extractor/_validate.py`
    - 扩展 `_TELEMETRY_ATTRIBUTE_KEYWORDS`：新增 `pulse`、`signal`、`transmission`、`latency`、`delay`、`coordinate`、`arcsecond`、`error`、`deviation`。
    - 新增 `_TELEMETRY_ALIAS_GROUPS`：信号/脉冲/传输、延迟/响应时间、坐标/误差/偏差。
    - 新增 `_is_telemetry_formula`：当 LLM 显式声明 `formula` 含 `telemetry` 时按遥测快照处理。
    - 更新 `_normalize_telemetry_snapshot`、`_find_telemetry_reading`、`_should_filter_unevidenced_numerical_update`，使公式兜底生效，同时避免有真实台账增减记录时被误过滤。
  - 新增回归测试：`tests/test_settlement_extractor.py`
    - `test_task138l_signal_pulse_latency_coordinate_telemetry_normalized`
    - `test_task138l_telemetry_formula_fallback_filters_without_evidence`
    - `test_task138l_unknown_attribute_name_but_telemetry_formula_normalized`
    - `test_task138l_real_ledger_with_telemetry_formula_still_validated`
  - 验证：
    - `_validate_settlement` 对 `rev-10-4-6988af8e` 的 Ch10 内容不再报 numerical formula 错误；
    - `pytest tests/test_settlement_extractor.py -q`：121 passed, 1 xfailed；
    - 全量 `pytest tests/ -q`：2007 passed, 1 xfailed, 2 warnings；
    - `ruff check src/ tests/` 通过。
  - 138k continuation 实跑验证：Ch10-Ch30 全部 settlement 通过，无 numerical formula 错误，Run `run-6f2a10d3` 30/30 完成。

## 关联

- 阻塞：`archive/v5/tasks/138k-long-window-rehearsal-ch1-ch50.md`
- 相关已完成：`archive/v5/tasks/138f-settlement-evidence-gated-numerical-extraction-DONE.md`

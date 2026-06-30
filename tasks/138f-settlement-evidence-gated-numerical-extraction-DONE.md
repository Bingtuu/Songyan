# Task 138f: Settlement 数值结算证据门禁工程化修复

> **类型**: 工程化修复 / 结算契约重构  
> **状态**: 已完成  
> **前置**: Task 138d-R2 latest retry `run-9f87da6f`  
> **目标**: 结束“每复跑一次补一个字段”的模式，让 numerical_update 只在有明确正文证据时进入硬结算。

## 1. 背景

Task 138d-R2 在多次 Ch10-Ch12 副本 DB retry 中连续暴露 settlement numerical_update 阻断：

- `left_leg_prosthetic_temperature`: 有正文温度读数，但原规则未覆盖无单位小数序列。
- `neural_pattern_match_rate`: 有明确百分比读数，但原规则未覆盖匹配度类读数。
- `beacon_core_countdown`: 有中文小时/分钟/秒倒计时读数，但原规则未换算为秒。
- `consciousness_upload_progress`: 最新 `run-9f87da6f` 输出 `closing_value=60.0`，但当前未找到明确 `60%/60.0` 正文读数证据。

前三类适合补窄 telemetry evidence 规则；第四类暴露出更大的工程问题：模型会从概念性正文推断结构化数值。继续按字段补丁追下去，会导致每次复跑都出现新 numerical_update 阻断。

## 2. 问题判断

当前不是单个字段缺口，而是 SettlementExtractor 的数值结算契约过度依赖 LLM：

| 层级 | 当前行为 | 风险 |
|------|----------|------|
| LLM 输出 | 同时发现字段、给出数值、编写公式 | 可能从概念描述中推断不存在的数值 |
| Validator | 有证据 telemetry 与无证据数值共用硬校验路径 | 一旦公式不闭合就阻断复跑 |
| 修复模式 | 每次复跑暴露一个新字段，再补一个规则 | 长跑成本高，因果判断被噪声污染 |
| 事实源 | numerical_update 可能写入无正文证据的结构化事实 | 破坏 SQLite 长期事实源可信度 |

## 3. 目标

Task 138f 的目标不是继续修 `consciousness_upload_progress` 这一个字段，而是建立工程化边界：

1. LLM 可以提出 numerical_update 候选，但不能凭空创造没有正文证据的数值。
2. 代码负责从 `content` / `source_quote` 中确认数字、单位、百分比或时间读数。
3. 有证据的 telemetry snapshot 可规整为快照。
4. 无证据的 numerical_update 不得进入硬结算；应被过滤、降级为 diagnostic，或触发明确 prompt/解析错误。
5. 真实 ledger 字段仍必须满足 `opening + increments - decrements == closing`，不能被 snapshot 规则吞掉。
6. 复跑前必须用离线 replay/eval 批量验证已有 Ch11/Ch12 阻断样本。

## 4. 范围

### 做

- 调查现有 SettlementExtractor parse/build/validate/apply 流程，确定最小插入点。
- 为 numerical_update 增加 evidence gate：
  - `telemetry_snapshot`: 必须能从正文或 `source_quote` 抽到与 `closing_value` 匹配的明确读数。
  - `ledger`: 必须公式闭合，且增减项 quote 不能自相矛盾。
  - `unevidenced`: 没有明确数值证据时不进入有效结算。
- 对 `consciousness_upload_progress` 建立回归样本：
  - 概念性文本“意识上传协议/正在读取”不能生成有效 numerical_update。
  - 明确文本“上传进度达到 60%”才允许 snapshot。
- 增加离线 replay/eval，至少覆盖 Task 138d-R2 暴露的 Ch11/Ch12 numerical_update 阻断样本。
- 更新 settlement prompt/card，明确“没有原文数字证据时禁止输出 numerical_update”。
- 目标测试和 `ruff check src/ tests/` 通过后，再允许启动新的 Ch10-Ch12 副本 DB retry。

### 不做

- 不放宽 `numerical_update.closing_value == formula` 硬约束。
- 不为 `consciousness_upload_progress` 增加无证据白名单。
- 不直接扩大到 Ch1-Ch20/default run。
- 不进入 Task 138e-R2，也不归档 Task 137。
- 不新增 Agent/Workflow 节点。

## 5. 任务拆分

- [x] SubTask 138f.1: 读取 `run-9f87da6f`、Ch11 `v-11-6-f0aea93b` 正文、source_quote、settlement payload 和 run log，确认 `consciousness_upload_progress=60.0` 是否有明确读数证据。
- [x] SubTask 138f.2: 设计 numerical_update evidence gate，区分 `telemetry_snapshot`、`ledger`、`unevidenced` 三类路径。
- [x] SubTask 138f.3: 实现最小代码修复：有证据 snapshot 规整；无证据 numerical_update 过滤/降级 diagnostic；真实 ledger 继续硬校验。
- [x] SubTask 138f.4: 更新 settlement_extractor prompt/card，禁止无原文数字证据的 numerical_update。
- [x] SubTask 138f.5: 补充单元测试，覆盖 `consciousness_upload_progress` 正例/负例、既有温度/匹配度/倒计时正例、真实 ledger 负例。
- [x] SubTask 138f.6: 增加或复用离线 replay/eval，批量验证 Task 138d-R2 暴露的 numerical_update 阻断样本。
- [x] SubTask 138f.7: 运行目标 pytest 与 `ruff check src/ tests/`。
- [x] SubTask 138f.8: 更新 Task 137/138d 文档、Ralph Loop 状态与事实入口，明确是否允许重新发起 138d-R2 copy-DB retry。

## 6. 验收标准

- `consciousness_upload_progress` 无明确 `60%/60.0` 证据时，不再作为有效 numerical_update 阻断复跑。
- 有明确读数证据的 telemetry snapshot 仍可规整通过。
- 真实 ledger 公式错误仍失败。
- 无证据 numerical_update 有可观测 diagnostic，不静默写入事实源。
- 离线 replay/eval 覆盖 Task 138d-R2 已知阻断样本。
- 目标 pytest 与 `ruff check src/ tests/` 通过。
- 完成后才允许重新发起新的 Ch10-Ch12 副本 DB retry。

## 7. 交付物

- `src/songyan/agents/settlement_extractor/` 最小代码改动。
- `prompts/cards/settlement_extractor/` prompt/card 更新。
- `tests/test_settlement_extractor.py` 或专门 replay/eval 测试。
- 可选：`scripts/` 下离线 replay/eval 工具。
- 本任务文档与 Ralph Loop 规格状态更新。

## 8. 完成记录

- 证据定位:
  - `run-9f87da6f` / Ch11 `v-11-6-f0aea93b` 正文存在“进度条”“大约三分之一”等概念性或图形化描述。
  - 正文未出现明确 `60.0`、`60%`、`60％`、`六十`、`百分之六十` 读数证据。
  - 因此 `consciousness_upload_progress=60.0` 判定为无证据 numerical_update 候选，不应继续作为硬结算阻断。
- 代码修复:
  - `_validate_settlement()` 在 numerical_update validation 中引入 evidence gate。
  - 有明确读数证据的 telemetry snapshot 继续规整为 `telemetry_snapshot`。
  - 无明确读数证据且公式不闭合的 telemetry numerical_update 会被过滤，并记录 `settlement.numerical_unevidenced_filtered` warning。
  - 非 telemetry 的真实 ledger 公式错误仍进入 `validation_errors`，不放宽硬校验。
- Prompt 修复:
  - `prompts/cards/settlement_extractor/1.0.2.yaml` 增加证据门禁要求：没有正文或 `source_quote` 明确数字证据时禁止输出 numerical_update。
  - 明确禁止把概念描述、趋势描述、图形化描述、估计或上下文常识换算成具体数值。
- 测试:
  - `tests/test_settlement_extractor.py` 增加 `consciousness_upload_progress` 正例/负例。
  - 复用 replay/eval 形式覆盖 `left_leg_prosthetic_temperature`、`neural_pattern_match_rate`、`beacon_core_countdown` 已知有证据 telemetry 阻断样本。
  - 保留真实 ledger 公式错误失败负例。
- 验证:
  - `python -m pytest tests/test_settlement_extractor.py -q` -> `111 passed, 1 xfailed in 18.83s`。
  - `ruff check src/songyan/agents/settlement_extractor/_validate.py tests/test_settlement_extractor.py` -> `All checks passed!`。
  - `ruff check src/ tests/` -> `All checks passed!`。
  - `python -m pytest tests/ -q` -> `1973 passed, 1 xfailed, 2 warnings in 299.26s`。
- 结论:
  - Task 138f 已完成。
  - 可以重新发起新的 Task 138d-R2 Ch10-Ch12 副本 DB retry，验证 Ch12 orphan 是否低于 baseline 16。

# Task 136: V5.2 enforce 模式 Ch1–Ch20 跨项目验证

> **类型**: 实跑验证 / 证据收集  
> **日期**: 2026-06-27  
> **前置**: Task 133（Writer 多场景结构）、Task 134（SettlementExtractor 提取修复）、Task 135（设定回收与 continuity health 治理）  
> **目标**: 在 enforce 模式下实跑 Ch1–Ch20，验证 Task 133/134/135 的修复效果，为是否将 `gate_mode="enforce"` / Writer 1.2.0 设为默认提供数据支撑。

---

## 1. 背景

Task 129（`run-89d7a2d4`，项目 ID `3cf71586df2a4b5c9170d9b1a5f059cf`）在 enforce 模式 Ch1–Ch50 验证中于 Ch15 后因 `quality_gate_fail_streak` 暂停，暴露出三个底层缺陷：

- **Writer 结构退化**：所有章节 `scenes_count=1`，导致 readability 在 Ch3/Ch14/Ch15 跌至 0.2–0.3。
- **SettlementExtractor 提取失败**：通过 QG 的章节 `character_states` 与 `numerical_ledgers` 记录数为 0。
- **设定回收失效**：`orphaned_settings` 从 Ch6 的 7 个快速上升到 Ch15 的 27 个，continuity health score 在 Ch12/Ch15 跌至 0.0。

Task 133/134/135 已分别针对上述问题完成代码与测试修复。本任务通过一次受控的 enforce 模式 Ch1–Ch20 实跑，收集修复后的第一手证据。

---

## 2. 验证设计

### 2.1 运行配置

- **Gate 配置**：使用 `GateConfig.for_mode("enforce")`（启用全部候选硬门禁），与 Task 129 的 enforce 定义保持一致。
- **Writer Prompt**：为验证 Task 133，需临时将 `prompts/cards/writer/_manifest.yaml` 的 `default_version` 从 `"1.1.0"` 切换为 `"1.2.0"`。
- **基线项目**：从 Task 129 源项目 `3cf71586df2a4b5c9170d9b1a5f059cf` 克隆配置，新建验证项目，确保与 `run-89d7a2d4` 可比。
- **章节范围**：Ch1–Ch20。
- **失败策略**：`on_failure="abort"`，记录 AutoHalt / pause 原因。

### 2.2 临时切换与回滚

```text
验证前：
1. git stash / 备份当前 manifest
2. 将 prompts/cards/writer/_manifest.yaml 的 default_version 改为 "1.2.0"

验证后：
1. 立即恢复 default_version 为 "1.1.0"
2. 只有在分析结果满足默认切换条件时，才在单独的 commit 中永久切换
```

### 2.3 采集指标

每章至少记录：

| 指标 | 来源 | 用途 |
|------|------|------|
| `quality_gate_passed` | `chapter_runs` JSONL | 总质量是否通过 |
| `convergence_failed` | `chapter_runs` JSONL | 收敛是否失败 |
| `settlement_success` | `chapter_runs` JSONL | settlement 是否成功 |
| `scenes_count` | `chapter_versions` + `parse_scenes()` | Task 133 |
| `character_states` 记录数 | `character_states` 表 | Task 134 |
| `numerical_ledgers` 记录数 | `numerical_ledgers` 表 | Task 134 |
| `continuity_health_score` | `continuity_reports` 表 | Task 135 |
| `orphaned_settings` 数量 | `continuity_reports` 表 | Task 135 |
| `gate_triggered` / `gate_reasons` | `chapter_runs` JSONL | 候选硬门禁是否误触发 |

---

## 3. 验收标准

### 3.1 Task 133 结构修复

- [ ] Ch1–Ch20 中 `scenes_count >= 2` 的章节占比 ≥ 90%（即 ≥ 18/20 章）。
- [ ] 没有章节因 readability 分数 < 0.5 而导致 QG 失败。

### 3.2 Task 134 提取修复

- [ ] 所有 `settlement_success=True` 的章节，`character_states` + `numerical_ledgers` 记录数 > 0。
- [ ] `old_value` 与 DB 当前值一致率 ≥ 95%（抽样检查主角字段）。
- [ ] `closing_value` 与公式计算值一致率 100%（由现有 validator 保证）。

### 3.3 Task 135 设定回收治理

- [ ] Ch15 时 `orphaned_settings` 增长速率 ≤ Ch12 时增长速率的一半（相对改善）。
- [ ] Ch12 与 Ch15 的 continuity health score 均 ≥ 3.0。

### 3.4 综合通过标准

- [ ] 进程至少成功到达 Ch20，或若提前 pause，则 pause 原因不得是上述三个已修复缺陷的回退。
- [ ] 与 `run-89d7a2d4` 同窗口（Ch1–Ch15）对比，QG 失败章节数下降 ≥ 50%。
- [ ] `ruff check src/ tests/` 通过。
- [ ] 输出 `archive/v5/reports/task-136-v52-enforce-ch1-ch20-validation-report.md`。

---

## 4. 执行步骤

1. 创建验证脚本 `scripts/run_136_v52_enforce_ch1_ch20_validation.py`：
   - 加载 source project `3cf71586df2a4b5c9170d9b1a5f059cf`。
   - 克隆为新项目。
   - 调用 `run_project_pipeline(project_id, chapter_range=(1, 20), gate_config=GateConfig.for_mode("enforce"), auto_confirm=True, on_failure="abort")`。
   - 运行结束后查询 DB 收集上述指标。
2. 临时切换 Writer manifest default_version → `"1.2.0"`。
3. 执行脚本，记录 run_id 与耗时。
4. 验证结束后立即恢复 Writer manifest default_version → `"1.1.0"`。
5. 生成报告并更新 `docs/STATUS.md` / `tasks/V5-README.md`。

---

## 5. 依赖关系

```
Task 133 Writer 多场景结构 ──┐
Task 134 Settlement 提取修复 ┼──► Task 136 V5.2 enforce Ch1–Ch20 验证
Task 135 设定回收治理 ────────┘
```

---

## 6. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| Writer 1.2.0 导致 observe 基线退化 | 破坏 `run-a2bed648` 证据 | 验证前后立即恢复 default_version，不在本任务中永久切换 |
| enforce 模式 Ch1–Ch20 仍因其他问题提前 pause | 无法采集完整指标 | 即使 pause，也记录 pause 原因与已跑章节的指标，作为后续任务输入 |
| LLM 调用成本高 / 时间长 | 验证耗时 ≈ 20 章 × 3–5 分钟 | 仅跑 Ch1–Ch20，不扩展到 Ch1–Ch150 |
| 候选硬门禁（health_low_p1_halt 等）误触发 | 进程提前终止 | 报告 gate_reasons，与 Task 129 对比；若为新问题则单独跟踪 |

---

## 7. 交付物

- `scripts/run_136_v52_enforce_ch1_ch20_validation.py`
- `archive/v5/reports/task-136-v52-enforce-ch1-ch20-validation-report.md`
- 更新后的 `docs/STATUS.md` 与 `tasks/V5-README.md`
- 本任务 `-DONE.md` 文档

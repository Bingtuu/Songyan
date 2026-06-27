# Task 130: 硬门禁默认模式决策 — DONE

> **类型**: 决策备忘录 / 工程收口  
> **日期**: 2026-06-27  
> **前置**: Task 124（离线影响面分析）、Task 125（阈值调优）、Task 126（Ch1–Ch20 enforce 验证）、Task 127（score halt 重构）、Task 128（严格模式容错与质量爬坡）、Task 129（Ch1–Ch50 enforce 验证）  
> **状态**: ✅ 完成  

---

## 1. 决策结论

**V5.1 默认保持 `gate_mode="observe"`**，同时暴露 `--gate-mode {observe|enforce}` CLI 参数供高级用户显式启用。

### 决策依据

1. `Task 129` enforce 模式验证（`run-89d7a2d4`）未跑通 Ch1–Ch50，在 Ch15 因 `quality_gate_fail_streak` 触发 AutoHalt。
2. 该验证暴露的不仅是阈值问题，而是**底层代码缺陷**：
   - Writer 输出 `scenes_count=1`，结构退化；
   - SettlementExtractor 未建立 `character_states` / `numerical_ledgers`；
   - `orphaned_settings` 快速累积，continuity health 跌至 0.0。
3. 这些缺陷在 observe 模式下被 `degraded_accept` 和 human_marks 掩盖；若默认 enforce，新用户首次长跑失败率会显著上升。
4. 阈值调优（Task 125）已在 `run-a2bed648` 上实现 `any_gate` 0 触发，证明**观测模式不会误伤**。

### V5.2 默认切换 enforce 的前提

必须先完成 **Task 133/134/135** 的底层缺陷修复，并在至少 2 个不同 genre/mode 项目上完成 Ch1–Ch150 enforce 实跑且 0 误触发。

---

## 2. 工程落地项

### 2.1 代码改动

| 文件 | 改动 |
|---|---|
| `src/songyan/models/gate_config.py` | 新增 `GateConfig.for_mode()` 工厂方法：`observe` 返回默认关闭配置，`enforce` 启用全部候选硬门禁 |
| `src/songyan/cli/main.py` | `songyan run` 新增 `--gate-mode {observe\|enforce}` 参数，默认 `observe`；将配置透传给 `run_project_pipeline` |
| `src/songyan/evals/streaming_report.py` | `songyan report` 输出新增候选硬门禁触发汇总：触发章节数、gate_mode 分布、触发原因明细 |

### 2.2 测试改动

| 文件 | 改动 |
|---|---|
| `tests/test_130_gate_mode.py` | 新增 7 个测试：help 文本、默认 observe、显式 observe、enforce 启用全部门禁、非法值拒绝、`GateConfig.for_mode()` 工厂方法 |
| `tests/test_105_streaming_validation.py` | 新增 1 个测试：报告 gate 汇总；扩展 `_make_log` helper 支持 gate 字段 |

---

## 3. 验收标准

- [x] 输出 `tasks/130-gate-mode-default-decision-DONE.md` 决策文档。
- [x] 文档中明确记录选择方案 A（默认保持 observe）+ 方案 E（暴露 CLI 参数）及其数据依据。
- [x] CLI 改动新增/更新对应测试并通过 pytest。
- [x] 全量 pytest / ruff 通过。
- [x] `docs/STATUS.md` 和 `tasks/V5-README.md` 同步更新 gate 默认模式口径。

---

## 4. 验证结果

```text
python -m pytest tests/ -q
1864 passed, 2 skipped, 1 xfailed

ruff check src/ tests/
All checks passed!
```

---

## 5. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 决策过早导致默认 enforce 误伤用户 | P1 | 默认保持 observe，直到跨项目证据充足 |
| 决策过晚导致硬门禁价值未释放 | P2 | 已暴露 `--gate-mode` 参数，高级用户可先行试用 |
| CLI 参数设计不当 | 用户体验差 | 与现有 `songyan run` 参数风格保持一致；使用 `click.Choice` 限制输入 |

---

## 6. 后续依赖

- **Task 131**：归档过时规划稿，更新索引文档指向 `-DONE.md`。
- **Task 132**：V5.1 最终验收包，汇总本任务成果。
- **Task 133/134/135（V5.2）**：修复 enforce 模式暴露的底层缺陷，为默认启用 enforce 提供证据。

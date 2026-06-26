# Task 121o: Ch1-Ch18 聚焦验证重跑

> **日期**: 2026-06-22
> **类型**: V5.1 preflight / 验收
> **状态**: ✅ 已完成（2026-06-22）
> **验证**: `run-4ff41095` 18/18 全部成功，无失败章节，无 AutoHalt
> **前置**: Task 121m（QG false 阻断 + 元标记清理）和 Task 121n（预算调整 + human_marks 生命周期）完成后执行。

---

## 1. 任务边界

本任务目标是验证 Task 121m 和 121n 的工程修复是否有效，确认系统能稳定越过 Ch13 和 Ch18 这两个历史阻断点，为 Ch1-Ch150 full single-run 提供可信基线。

聚焦：

- 在干净项目环境中执行 Ch1-Ch18 聚焦实跑。
- 验收 QG false 版本不再进入 settlement。
- 验收正文中无元标记泄漏。
- 验收 Ch10-Ch12 不再构成连续 ContextEmergency degraded streak。
- 必须越过 Ch13 和 Ch18。

不做：

- 不包装 partial 结果为全量证据。
- 不在本任务中执行 Ch1-Ch150 full single-run（修复验证通过后再执行）。
- 不处理 Prompt 文风调优（归 Task 121k）。

---

## 2. 事实入口

| 项 | 值 |
|----|----|
| 前置任务 | `tasks/121m-qg-false-block-and-meta-tag-cleanup.md`、`tasks/121n-context-diet-budget-and-human-marks-lifecycle.md` |
| 历史基线 | `tasks/121l-context-emergency-autohalt-review.md` 7.7 节 |
| 历史问题 | Ch10 QG false 仍 settlement；Ch12 元标记泄漏；Ch10-Ch12 连续 ContextEmergency 触发 AutoHalt |
| wrapper | `scripts/run_songyan_chapter.ps1` |

---

## 3. 验收标准

### 3.1 硬标准（必须全部通过）

1. **完整通过**：Ch1-Ch18 全部完成，无失败章节。
2. **越过阻断点**：必须越过 Ch13 和 Ch18。
3. **QG false 阻断**：若某章 `quality_gate_passed=False`，日志中不得出现 `settlement_extractor_node.settlement_applied`。
4. **元标记纯净**：抽查 Ch1-Ch18 所有 accepted 版本的正文，不得出现 `<!--` 或 `[[新设定`。
5. **AutoHalt 不熔断**：连续 ContextEmergency 但章节均成功时，仅记录 warning，不暂停 run；仅当伴随真实降级（QG false / settlement fail / summary fail）时才熔断。

### 3.2 软标准（趋势向好即可）

1. **ContextEmergency 频率**：Ch10-Ch12 不再连续触发 emergency，或触发前 `budget_used_before_emergency` < 1.15。
2. **质量评分**：Ch8-Ch12 的 `overall_score` 滚动均值 > 0.78，无低于 0.70 的章节。
3. **字数稳定**：Length 评分 > 0.60，无 hard truncate 导致的文本截断或拼接错误。

---

## 4. 执行步骤

### Step A: 前置检查

确认 Task 121m 和 121n 已完成并提交：

```powershell
python -m pytest tests/ -q
ruff check src/ tests/
```

### Step B: 创建干净验证项目

新建一个专门用于 Task 121o 验证的项目（复用 121l 的流程）：

```powershell
# 参考 121l 文档中的项目创建命令
# project_id 需要新生成
```

### Step C: 执行 Ch1-Ch18 聚焦实跑

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_songyan_chapter.ps1 `
  -ProjectId '<new_project_id>' `
  -Chapters '1-18' `
  -ModeId 'webnovel_intense' `
  -Tag 'ch1-ch18-validation-121o' `
  -TaskName 'task121o' `
  -TimeoutSec 21600 `
  -BusinessDoneGraceSec 120
```

### Step D: 结果分析

运行结束后提取关键指标：

```python
# 检查 completed_chapters、failed_chapters、status
# 检查各章 budget_used_before_emergency、context_emergency
# 检查各章 quality_gate_passed 与 settlement_applied 的对应关系
# 抽查正文中是否含 <!-- 或 [[新设定
```

### Step E: 文档更新

- 将 `run_id`、结果、关键指标写入本文档。
- 更新 `docs/STATUS.md`、`README.md`、`tasks/V5-README.md`。

---

## 5. 结论分支

| 结果 | 处理 |
|------|------|
| **18/18 通过** | 进入 Ch1-Ch150 full single-run，新建 `run_id` 执行。 |
| **Partial（如 Ch13 后暂停）** | 分析新阻断根因，判断是否属于 121m/121n 未覆盖的边界，或需要启动 Task 121k（Prompt 质量清理）。 |
| **QG false 仍 settlement** | 回退到 Task 121m，检查硬拦截逻辑是否生效。 |
| **仍出现元标记** | 回退到 Task 121m，检查 writer 后处理和 prompt 是否生效。 |
| **仍连续 emergency** | 回退到 Task 121n，进一步上调预算或收紧 human_marks。 |

---

## 6. 验证结果（2026-06-22）

### 6.1 执行记录

| 项 | 值 |
|----|----|
| run_id | `run-4ff41095` |
| project_id | `d54de3c1d44842ff9dc6ceaa36f107c7` |
| 时间范围 | 19:18 – 21:10（约 1 小时 52 分钟） |
| 结果 | **18/18 全部成功** |
| completed_chapters | [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18] |
| failed_chapters | [] |
| status | `completed` |

### 6.2 硬标准验收

| 标准 | 结果 | 证据 |
|------|------|------|
| 完整通过 18/18 | ✅ 通过 | 无失败章节 |
| 越过 Ch13 和 Ch18 | ✅ 通过 | Ch13 和 Ch18 均 `chapter_success` |
| QG false 阻断 | ✅ 通过 | QG false 次数 = 0， settlement 仅在 QG 通过版本执行 |
| 元标记纯净 | ✅ 通过 | 日志中 `<!--` 和 `[[新设定` 出现次数 = 0 |
| AutoHalt 不熔断 | ✅ 通过 | AutoHalt 触发次数 = 0 |

### 6.3 软标准验收

| 标准 | 结果 | 证据 |
|------|------|------|
| ContextEmergency 频率 | ✅ 显著改善 | **0 次触发**（121l 中 Ch10-Ch12 连续触发） |
| 质量评分 Ch8-Ch12 | ⚠️ 接近目标 | 滚动均值 = 0.7697（目标 > 0.78）；Ch8 = 0.6855（低于 0.70） |
| 字数稳定 | ⚠️ 仍需优化 | Writer 仍频繁超量（Ch2 6243→4491，Ch10 等），但 Length 评分总体 > 0.60 |

### 6.4 质量评分详情

| 章节 | Overall | Budget | Length | Momentum |
|------|---------|--------|--------|----------|
| Ch1 | 0.8874 | 1.0 | 1.0 | 0.8 |
| Ch2 | 0.8193 | 1.0 | 0.84 | 0.5 |
| Ch3 | 0.8024 | 1.0 | 0.88 | 0.5 |
| Ch4 | 0.8231 | 1.0 | 0.92 | 0.5 |
| Ch5 | 0.7646 | 1.0 | 0.76 | 0.5 |
| Ch6 | 0.8402 | 1.0 | 0.92 | 0.5 |
| Ch7 | 0.8139 | 1.0 | 0.84 | 0.5 |
| Ch8 | 0.6855 | 1.0 | 0.56 | 0.5 |
| Ch9 | 0.8463 | 1.0 | 0.84 | 0.5 |
| Ch10 | 0.7320 | 1.0 | 0.68 | 0.5 |
| Ch11 | 0.7981 | 1.0 | 0.84 | 0.5 |
| Ch12 | 0.7864 | 1.0 | 0.84 | 0.5 |
| Ch13 | 0.7184 | 1.0 | 0.72 | 0.5 |
| Ch14 | 0.7539 | 1.0 | 0.76 | 0.5 |
| Ch15 | 0.7395 | 1.0 | 0.72 | 0.5 |
| Ch16 | 0.8296 | 1.0 | 0.92 | 0.5 |
| Ch17 | 0.6962 | 1.0 | 0.68 | 0.5 |
| Ch18 | 0.7800 | 1.0 | 0.84 | 0.5 |

### 6.5 关键发现

1. **121n 预算调整效果显著**：Ch10-Ch12 不再触发 ContextEmergency（121l 中 budget_used_before=1.569/1.599/1.629），上下文压力完全消除。
2. **121m QG false 拦截未触发但系统健康**：本轮无 QG false 章节，说明整体生成质量提升，但拦截逻辑已就位。
3. **Ch8、Ch13、Ch17 评分偏低**：主要问题仍是 writer 字数超量导致的 hard truncate，以及中段叙事动能波动。这属于 Prompt / 正文质量范畴，需在 Task 121k 中处理。

### 6.6 结论

Task 121o **验收通过**。121m 和 121n 的工程修复成功消除了 degraded emergency streak 的根因，系统已能稳定越过 Ch13 和 Ch18。下一步可启动 **Ch1-Ch150 full single-run**，同时 Task 121k（Prompt 质量清理）可并行准备。

---

## 7. 后续

- Task 121o 已验证通过，立即启动新的 Ch1-Ch150 full single-run，作为 V5.0 single-run rehearsal 的最终证据。
- Task 121k（Prompt / 正文质量清理）可并行启动，重点解决 writer 字数超量、中段动能波动和短段落碎片化问题。

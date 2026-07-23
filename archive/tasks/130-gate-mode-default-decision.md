# Task 130: 硬门禁默认模式决策

> **类型**: 决策备忘录 / 工程收口  
> **日期**: 2026-06-26  
> **前置**: Task 124（离线影响面分析）、Task 125（阈值调优）、Task 126（Ch1–Ch20 enforce 验证）、Task 127（score halt 重构）、Task 128（严格模式容错与质量爬坡）、Task 129（Ch1–Ch50 enforce 验证）  
> **目标**: 基于已有证据，决定 `gate_mode` 在 V5.1 中的默认值，并形成可执行的工程结论。

---

## 1. 背景与问题

当前 `GateConfig` 默认 `mode="observe"`，即 gate 只记录不阻断。经过 Task 123–128 的预研后，需要回答：

- V5.1 是否应将默认模式切换为 `enforce`？
- 如果切换，是全局切换还是按条件切换？
- 如果保持 `observe`，V5.2 还需要哪些证据才能切换？

这个决策直接影响用户默认体验和长跑成功率，必须基于数据而非直觉。

---

## 2. 可选决策方案（Brainstorming）

### 方案 A：保持默认 `observe`
- **做法**：V5.1 不改默认模式，继续以观测模式收集数据。
- **优点**：零风险，不破坏当前 150 章跑通能力；用户手动启用 enforce 时才生效。
- **缺点**：硬门禁价值无法自动发挥；用户可能不知道需要开启。
- **适用**: 若 Task 128 仍有误触发或证据不足。

### 方案 B：默认切换为 `enforce`
- **做法**：将 `GateConfig` 默认值改为 `mode="enforce"`。
- **优点**：健康监护自动生效；符合 V5.1 "质量收口"定位。
- **缺点**：一旦阈值仍有缺陷，会提高新用户首次长跑的失败率。
- **适用**: 若 Task 126 + Task 128 连续 0 误触发，且离线分析（Task 124）显示调优后 any_gate 触发 0 章。

### 方案 C：按章节窗口切换（渐进 enforce）
- **做法**：Ch1–ChN 为 `observe`，ChN+1 后为 `enforce`。
- **优点**：避开开局期波动；后段质量风险更高，更需要硬门禁。
- **缺点**：增加复杂度；N 的选择需要数据支撑。
- **适用**: 若开局期误触风险无法完全消除。

### 方案 D：按项目成熟度切换
- **做法**：新项目前几次 run 默认 `observe`，收集到足够 continuity 数据后自动切换 `enforce`。
- **优点**：自适应，避免 cold start 误触发。
- **缺点**：需要定义"足够数据"的阈值；实现复杂。
- **适用**: V5.2 方向。

### 方案 E：CLI/配置暴露给用户
- **做法**：无论默认是什么，`songyan run` 增加 `--gate-mode {observe|enforce}` 参数，用户可显式选择。
- **优点**：灵活性最高；不同风险偏好用户自选。
- **缺点**：用户需要理解 gate 概念；默认选择仍需要决策。
- **适用**: 与 A/B/C/D 任一方案组合使用。

---

## 3. 推荐方案

**阶段化推进**：

1. **V5.1 默认保持 `observe`**（方案 A），因为：
   - 硬门禁是新增能力，需要先让用户/测试在观测模式下习惯其存在。
   - Task 129 只覆盖到 Ch15，且暴露出底层提取/结构缺陷，不足以证明 Ch1–Ch150 的泛化性。
   - V5.1 核心目标是"可观测、可配置、阈值合理"，而非"默认阻断"。

2. **V5.1 必须暴露 `--gate-mode` CLI 参数**（方案 E），让高级用户和风险偏好高的用户可以显式启用 enforce。

3. **V5.2 默认切换为 `enforce` 的前提**：
   - 在至少 2 个不同 genre/mode 项目上完成 Ch1–Ch150 enforce 实跑，0 误触发。
   - 或完成跨项目泛化验证（Task 133 方向）。

---

## 4. 决策依据清单

### 4.1 必须收集的证据

| 证据来源 | 状态 | 说明 |
|---------|------|------|
| Task 124 离线影响面 | ✅ 已完成 | 原始阈值触发 118/120 章；调优后 0 章 |
| Task 125 阈值调优 | ✅ 已完成 | `run-a2bed648` 上 `any_gate` 0 触发 |
| Task 126 Ch1–Ch20 enforce | ✅ 已完成 | 0 gate 触发（禁用 score_drop 后） |
| Task 127 score halt 重构 | ✅ 已完成 | 解决开局期误触发 |
| Task 128 严格模式容错 | ✅ 已完成 | 修复 QG false 阻断 run；pytest 1856 passed |
| Task 129 Ch1–Ch50 enforce | ⚠️ 条件完成 | `run-89d7a2d4` Ch1–Ch15 后因 quality_gate_fail_streak 暂停；详见 `archive/v5/reports/task-129-enforce-validation-report.md` |

### 4.2 决策规则

```
IF Task 129 结果 == 成功（0 gate 触发）
   AND Task 127 重构通过
   AND Task 128 修复通过
THEN V5.1 默认保持 observe，但暴露 CLI 参数
     V5.2 默认切换 enforce 的条件：
       1. 完成 Task 133/134/135 的底层缺陷修复；
       2. 在至少 2 个不同 genre/mode 项目上完成 Ch1–Ch150 enforce 实跑，0 误触发。
ELSE IF Task 129 出现 1 次条件成功（真异常触发）
THEN V5.1 保持 observe，将 enforce 作为推荐手动选项；
     V5.2 默认切换 enforce 仍需先完成 Task 133/134/135。
ELSE IF Task 129 出现误伤
THEN 回滚 Task 125/127 调优，V5.1 不推进 enforce
```

> **实际判定**：`Task 129` 在 `run-89d7a2d4` 中 Ch15 因 quality gate streak 暂停，且报告暴露出 Writer 结构退化、SettlementExtractor 角色/数值提取失败、orphaned settings 快速累积等底层缺陷。因此：
> - **V5.1 默认保持 `observe`**；
> - **V5.1 暴露 `--gate-mode` CLI 参数**；
> - **V5.2 默认切换 `enforce` 被 Task 133/134/135 阻塞**，需在修复后重新完成 Ch1–Ch150 enforce 验证。

---

## 5. 工程落地项

### 5.1 若选择默认保持 observe
- [ ] 确认 `GateConfig(mode="observe")` 仍是默认。
- [ ] 在 `songyan run` CLI 中增加 `--gate-mode {observe|enforce}` 参数。
- [ ] 在 `songyan report` 中增加 gate 触发汇总，让用户即使 observe 也能看到风险。
- [ ] 文档中明确说明：默认 observe 是为了不破坏长跑；需要 enforce 可显式开启。

### 5.2 若选择默认切换 enforce
- [ ] 将 `GateConfig` 默认值改为 `mode="enforce"`。
- [ ] 在 CLI 中保留 `--gate-mode observe` 选项，允许回退。
- [ ] 更新所有默认配置文档和示例。
- [ ] 新增集成测试：验证默认 enforce 下正常单章 pipeline 不被误伤。

---

## 6. 验收标准

- [ ] 输出 `archive/v5/tasks/130-gate-mode-default-decision-DONE.md` 决策文档。
- [ ] 文档中明确记录选择方案 A/B/C/D/E 中的哪一个及其数据依据。
- [ ] 若涉及 CLI 改动，新增/更新对应测试并通过 pytest。
- [ ] 全量 pytest / ruff 通过。
- [ ] `docs/STATUS.md` 和 `tasks/V5-README.md` 同步更新 gate 默认模式口径。

---

## 7. 依赖关系

```
Task 124/125 离线分析与阈值调优 ──┐
Task 126 Ch1-Ch20 enforce ────────┤
Task 127 score halt 重构 ─────────┼──► Task 130 默认模式决策
Task 128 严格模式容错 ────────────┤
Task 129 Ch1-Ch50 enforce ────────┘
```

---

## 8. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 决策过早导致默认 enforce 误伤用户 | P1 | 默认保持 observe，直到跨项目证据充足 |
| 决策过晚导致硬门禁价值未释放 | P2 | 先暴露 CLI 参数，让高级用户先行试用 |
| CLI 参数设计不当 | 用户体验差 | 与现有 `songyan run` 参数风格保持一致 |

---

## 9. 交付物

- `archive/v5/tasks/130-gate-mode-default-decision-DONE.md`
- CLI 改动（如需）：`src/songyan/cli/` 相关文件
- 新增/更新测试
- 全量 pytest / ruff 通过记录
- `docs/STATUS.md`、`tasks/V5-README.md` 更新

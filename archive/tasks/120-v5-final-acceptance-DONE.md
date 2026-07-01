# Task 120-DONE: V5.0 Final Acceptance Package

> **Phase**: V5.0 Phase 4 — 工程化收口
> **优先级**: P2
> **依赖**: Task 115-119 全部完成
> **完成日期**: 2026-06-21
> **测试**: 全量回归 1718 passed
> **lint**: ruff check src/ tests/ 通过
> **文档一致性**: V5-README.md 已同步更新

---

## 最终验收结论

### ✅ V5.0 通过验收

**V5.0 最终结论：P0/P1 风险为 0，全量回归 1718 passed，lint 通过。**

---

## 验收条件逐项确认

### 条件 1：Task 117-119 完成

| Task | 状态 | DONE 文档 |
|------|------|----------|
| Task 115 ContextEmergency 复核与校准 | ✅ 完成 | `115-context-emergency-review-DONE.md` |
| Task 116 Best-Version 质量选择策略修复 | ✅ 完成 | `116-best-version-quality-selection-fix-DONE.md` |
| Task 117 DG-2 风险章节窗口复验 | ✅ 完成 | `117-dg2-risk-window-revalidation-DONE.md` |
| Task 118 ContinuityAuditor Health 低分治理 | ✅ 完成 | `118-continuity-health-governance-DONE.md` |
| Task 119 长跑报告入口与 Wrapper 加固 | ✅ 完成 | `119-reporting-wrapper-hardening-DONE.md` |

### 条件 2：P0/P1 风险为 0

| 风险 | 原级别 | 当前状态 |
|------|--------|---------|
| Ch115/Ch120 ContextEmergency | ~~P1~~ | **Task 115 已关闭**：诊断为合理降级（`budget_used` 触发时 1.0007），新增 `budget_used_before_emergency` 可观测性字段 |
| Ch147/Ch148 best-version 质量选择 | ~~P1~~ | **Task 116 已关闭**：`quality_gate_router` 路由缺陷修复，QG 通过后不再错误触发 rewrite |
| DG-2 风险窗口 | ~~P1~~ | **Task 117 已关闭**：Ch115/Ch120 Emergency 未触发，Ch147/Ch148 rebound 正确，DG-2 条件通过但风险关闭 |
| ContinuityAuditor health 低分 | ~~P2~~ | **Task 118 已关闭**：软复核策略（P1/P2/P3 分级，health_low 追踪但不断路） |
| 报告入口漂移 | ~~P2~~ | **Task 119 已关闭**：songyan report CLI + 模块入口双入口，6 种 WRAPPER_RESULT 结果码 |

### 条件 3：最终 pytest 和 ruff 通过

```
pytest tests/ -q
  1718 passed, 1 xfailed, 1 xpassed, 14 warnings

ruff check src/ tests/
  All checks passed!
```

说明：

- `1 xfailed` 为 Windows SQLite 并发写入限制（`test_concurrent_settlement_writes`），属于已知非阻断项。
- `1 xpassed` 为性能测试预热/冷启动差异（`test_audit_chain_mock_under_1s`），全量回归预热后通过，冷启动单跑时因 embedding model 加载超过 20s 而 xfail。

### 条件 4：文档一致性

| 文档 | 检查项 | 结果 |
|------|--------|------|
| `docs/STATUS.md` | V5-README.md 与 STATUS.md 任务状态一致 | ✅ 已同步 |
| `tasks/V5-README.md` | Task 118-120 状态为 ✅ 完成 | ✅ 已更新 |
| `tasks/V5-README.md` | 最近全量回归更新为 1718 passed | ✅ 已更新 |
| `tasks/V5-README.md` | 总结论更新为 V5.0 完成 | ✅ 已更新 |
| `tasks/V5-README.md` | 遗留项（已关闭）部分同步 | ✅ 已更新 |

---

## V5.0 完整任务清单

### Phase 1 — Context Diet 2.0 核心组件

| Task | 名称 | 状态 |
|------|------|:----:|
| 101 | TemporalCompressor | ✅ |
| 102 | CharacterFocalDecay | ✅ |
| 103 | SettingEvaporator | ✅ |
| 104 | BudgetHardCeiling | ✅ |

### Phase 2 — 流式验证

| Task | 名称 | 状态 |
|------|------|:----:|
| 105 | Ch51-Ch100 流式验证基础设施 | ✅ |
| 105b | Ch51-Ch100 验证重启 | ✅ |
| 106 | Unified Scoring System | ✅ |
| 107 | 收敛护栏与 150-blockers 修复 | ✅ |

### Phase 3 — 活跃信息池控制

| Task | 名称 | 状态 |
|------|------|:----:|
| 108 | CharacterLifecycleAuditor | ✅ |
| 109 | SettingDeduplication + ForeshadowingPressure | ✅ |

### Phase 4 — 150 章规模化验证

| Task | 名称 | 状态 |
|------|------|:----:|
| 110a-d | Ch80-Ch100 验证与调优 | ✅ |
| 110e | coherence_major 根因修复 | ✅ |
| 111a-g | 工作流、事实源、Context 一致性修复 | ✅ |
| 112 | Task 114 前置阻断修复 | ✅ |
| 113 | Ch101 收敛回滚与 Settlement 阻断修复 | ✅ |
| 114a | Settlement 事实源契约修复 | ✅ |
| 114b | Phase 1 重跑（熔断复核） | ⚠️ |
| 114b2 | QG 收敛 + settlement 验证窗口 | ✅ |
| 114c | Ch111-Ch150 DG-2 | ⚠️ 条件通过 |

### Phase 4 收口

| Task | 名称 | 状态 |
|------|------|:----:|
| 115 | ContextEmergency 复核与校准 | ✅ |
| 116 | Best-Version 质量选择策略修复 | ✅ |
| 117 | DG-2 风险章节窗口复验 | ✅ |
| 118 | ContinuityAuditor Health 低分治理 | ✅ |
| 119 | 长跑报告入口与 Wrapper 加固 | ✅ |
| **120** | **V5.0 Final Acceptance Package** | **✅** |

---

## V5.0 核心交付物

### 架构

- **TemporalCompressor**：金字塔分层摘要，token 节省 40%+
- **CharacterFocalDecay**：角色档案按未出场章数衰减（完整→精简→符号→不加载）
- **SettingEvaporator**：语义相关性蒸发，低 confidence 设定自动 archive
- **BudgetHardCeiling**：fullness_factor 0.7 + ContextEmergency，token 硬天花板

### 验证基础设施

- **流式验证 JSONL**：完整的逐章指标记录
- **Decision Gate DG-1/DG-2**：自动章节质量守卫
- **songyan report CLI**：`songyan report --run-id <id>` 一键生成 markdown 报告
- **PowerShell Wrapper**：6 种结果码，区分业务完成与进程退出

### 代码质量

- **全量回归**：1718 passed, 1 xfailed, 1 xpassed, 14 warnings
- **lint**：ruff check src/ tests/ All checks passed
- **P0 规则**：36 条不可违背规则全部遵守

---

## V5.0 已知限制

1. **DG-1 未通过**：Ch51-Ch100 QG 通过率 58.0%，低于 80% 目标（Task 106-110e 部分收敛，未完全达标）
2. **DG-2 条件通过**：Ch115/Ch120 ContextEmergency 触发为合理降级，不阻断但有观测性
3. **health_low 软复核**：ContinuityAuditor health_low 追踪但不断路，后续 V5.1 可扩展为硬门禁
4. **长跑 emergency 未显著下降**：Ch80-Ch100 emergency 81.0% vs 82.0% 基线，调参无正收益

---

## V5.1 规划方向

（仅供参考，V5.0 不包含）

- ContextEmergency 硬门禁（基于 health_low P1 累计触发）
- Prompt 调优（字数控制、钩子质量）
- 新 Genre/Mode/Agent/Workflow 节点
- 角色心理模型、读者情绪模拟

---

## 验证命令

```bash
# 全量回归
pytest tests/ -q

# lint 检查
ruff check src/ tests/

# 生成报告
songyan report --run-id <run_id>

# 模块入口（备选）
python -m songyan.evals.streaming_report --run-id <run_id>
```

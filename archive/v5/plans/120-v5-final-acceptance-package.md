# Task 120: V5.0 Final Acceptance Package

> **Phase**: V5.0 Phase 4 — 最终验收与收口
> **优先级**: P2
> **依赖**: Task 115、116、117、118、119 完成
> **预计工作量**: 1-2 天

---

## Goal

整理 V5.0 最终验收包，统一代码、测试、长跑报告、任务文档和状态文档，给出 V5.0 的最终结论：正式通过、条件通过并关闭风险，或转入 V5.1 继续处理。

## Context

V5.0 的目标是通过 Context Diet 2.0 支撑 Ch1-Ch150 全自动稳定生成。Task 114c 已经完成 Ch111-Ch150 40/40 成功，但 DG-2 为条件通过，后续 Task 115-119 将处理 emergency、best-version、风险窗口复验、health_low 和报告/wrapper 工程化问题。

Task 120 是 V5.0 的最终收口任务，不再承担新功能开发。它的职责是把事实证据整理为可审计的最终验收包，并明确 V5.1 是否启动。

## In Scope（必须完成）

- [ ] 汇总 V5.0 Task 101-119 的最终状态。
- [ ] 汇总 DG-1、DG-2、Task 117 复验报告和关键指标。
- [ ] 运行最终测试与 lint。
- [ ] 检查 `tasks/V5-README.md`、`docs/STATUS.md`、`README.md`、`docs/INDEX.md` 状态一致。
- [ ] 生成 `tasks/120-v5-final-acceptance-package-DONE.md`。
- [ ] 明确 V5.0 最终判定和 V5.1 候选任务。

## Out of Scope（明确不做）

- 不新增业务功能。
- 不修改评分阈值。
- 不启动新一轮 Ch111-Ch150 全量长跑，除非 Task 117 失败且要求重跑。
- 不把 V5.1 预研任务混入 V5.0 验收标准。

## 实现方案

### 1. 最终证据清单

验收包至少包含：

| 证据 | 来源 |
|------|------|
| V5 task 状态总表 | `tasks/V5-README.md` |
| Task 114c DG-2 报告 | `archive/v5/reports/report-task114c-dg2-ch111-ch150.md` |
| Task 117 风险窗口复验报告 | Task 117 DONE |
| 全量 pytest | 最新测试输出 |
| 全量 ruff | `ruff check src/ tests/` |
| 文档一致性 | STATUS/README/INDEX/V5-README |
| 未解决风险 | Task 118/119/120 汇总 |

### 2. 最终判定规则

| 判定 | 条件 |
|------|------|
| V5.0 通过 | DG-2 关键风险关闭；最终测试/lint 通过；文档一致 |
| V5.0 条件通过 | 仍有 P2/P3 质量复核项，但无 P0/P1 阻断 |
| V5.0 不通过 | 存在未关闭 P0/P1，或 final tests/lint 失败 |

### 3. 文档收口

所有入口文档必须同口径：

- `tasks/V5-README.md`：最高优先级事实入口。
- `docs/STATUS.md`：当前阶段状态板。
- `README.md`：项目首页摘要。
- `docs/INDEX.md`：文档索引。

状态不得出现以下冲突：

- 一个文档说 Task 114c 进行中，另一个说完成。
- 一个文档说 DG-2 通过，另一个说条件通过。
- 规划稿被当作 DONE 证据。
- 旧报告入口被标记为推荐入口。

### 4. V5.1 候选清单

Task 120 只整理候选，不展开实现：

- ContinuityAuditor 是否升级为硬门禁。
- 文学质量人工抽样与自动指标对齐。
- 长跑更大窗口或 Ch151+ 验证。
- Prompt/scorecard 质量策略优化。

## 接口契约

```bash
pytest tests/ -q
ruff check src/ tests/
```

可选文档一致性检查：

```bash
rg "当前 Task|DG-2|Task 114c|Task 115|Task 120" README.md docs tasks
```

如项目已有文档校验脚本，应优先使用。

## 数据模型

不新增业务模型。验收包可使用 markdown 表格表达：

```python
class FinalAcceptanceItem(BaseModel):
    name: str
    status: Literal["passed", "conditional", "failed", "not_applicable"]
    evidence: str
    notes: str | None = None
```

## 执行流程

1. **前置确认**
   - 确认 Task 115-119 DONE 文件存在。
   - 确认所有 P1 风险有结论。

2. **验证运行**
   - 执行 `ruff check src/ tests/`。
   - 执行 `pytest tests/ -q`，按 Windows 防卡协议处理 teardown timeout。

3. **证据汇总**
   - 汇总 DG-2、风险窗口复验、health_low、report/wrapper 状态。
   - 记录最新 run id、报告路径和测试输出。

4. **文档同步**
   - 更新 `tasks/V5-README.md`。
   - 更新 `docs/STATUS.md`。
   - 更新 `README.md`。
   - 更新 `docs/INDEX.md`。

5. **一致性校验**
   - 检查核心状态关键词。
   - 检查 markdown 引用文件存在。
   - 执行 `git diff --check`。

6. **最终交付**
   - 生成 `tasks/120-v5-final-acceptance-package-DONE.md`。
   - 给出 V5.0 最终判定和 V5.1 建议。

## 测试要求

### Layer 1: 质量检查

- [ ] `ruff check src/ tests/` 通过。
- [ ] `pytest tests/ -q` 通过，或按防卡协议记录明确 pass 状态。

### Layer 2: 文档检查

- [ ] `tasks/V5-README.md` 与 STATUS/README/INDEX 状态一致。
- [ ] 所有新增 DONE 文档被索引。
- [ ] 旧规划稿不作为完成证据。
- [ ] Markdown 文件引用存在。

### Layer 3: 验收检查

- [ ] Task 115-119 均有明确 DONE 结论。
- [ ] P0/P1 风险为 0。
- [ ] P2/P3 风险有 V5.1 候选任务或接受说明。

## 验收标准（Acceptance Criteria）

| 指标 | 目标 |
|------|------|
| Task 115-119 | 全部完成并有 DONE 文档 |
| P0/P1 未解决风险 | 0 |
| final pytest | 通过 |
| final ruff | 通过 |
| 文档一致性 | STATUS/README/INDEX/V5-README 同口径 |
| V5.0 最终判定 | 明确为通过、条件通过或不通过 |
| V5.1 候选 | 清单明确，但不混入 V5.0 交付范围 |

## 风险与应对

| 风险 | 应对 |
|------|------|
| 验收时发现新 P1 | 停止收口，拆分新任务，不强行关闭 V5.0 |
| pytest 长时间 teardown 卡住 | 按 AGENTS Windows 防卡协议判定和清理 |
| 文档状态再次漂移 | 以 `tasks/V5-README.md` 和 `*-DONE.md` 为事实源 |
| V5.1 范围膨胀 | Task 120 只列候选，不实现 |

## 参考文档

- `tasks/V5-README.md`
- `tasks/114-ch101-ch150-streaming-validation-DONE.md`
- `archive/v5/plans/115-context-emergency-review.md`
- `archive/v5/plans/116-best-version-quality-selection-fix.md`
- `archive/v5/plans/117-dg2-risk-window-revalidation.md`
- `archive/v5/plans/118-continuity-health-governance.md`
- `archive/v5/plans/119-reporting-wrapper-hardening.md`
- `docs/STATUS.md`
- `README.md`
- `docs/INDEX.md`

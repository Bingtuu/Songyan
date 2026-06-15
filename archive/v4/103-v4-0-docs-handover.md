# Task 103: V4.0 Phase B 文档交接 + 决策门 1 评估

> **Phase**: V4.0 Phase B — 交付
> **优先级**: P0
> **依赖**: Task 100c（修复收尾完成）
> **预计工作量**: 小（1-2 天）

---

## Goal

完成 V4.0 Phase B 的文档更新、交接报告和决策门 1 评估。

---

## Context

### 决策门 1

Phase B 的验收结果将决定 V4.0 的下一步：

```
决策门 1
    │
    ├─ 达标（100 章成功）→ V4.0 Phase B 收尾 → 进入 V4.1 优化
    │
    ├─ 有条件达标（100 章完成但有已知限制）→ V4.0 Phase B 收尾 → 记录限制 → V4.1 修复
    │
    └─ 不达标（100 章失败）→ 评估原因 → 可能需要 Phase C（ContextService）
```

### 需要回答的问题

1. **字数控制**：达标率是否达到可接受水平？
2. **Context Budget**：token_budget 是否可控？
3. **Health Score**：连续性追踪是否可靠？
4. **成本**：100 章总成本是否在预算内？
5. **扩展性**：能否支撑到 200 章？300 章？

---

## In Scope（必须完成）

### 1. 更新 docs/STATUS.md

将 Phase B 的最终结果写入 STATUS：

```markdown
## V4.0 Phase B 结果

| 指标 | 目标 | 实际 | 判定 |
|------|------|------|------|
| 100 章全自动 | 0 失败 | ? | ? |
| 字数达标率 | > 65% | ? | ? |
| budget_used 平均 | < 1.3 | ? | ? |
| health_score 平均 | ≥ 3.0 | ? | ? |
| token_budget 平均 | < 1.3 | ? | ? |
| 总成本 | < ¥X | ? | ? |
```

### 2. 生成综合报告

生成 `docs/v4-0-phase-b-report.md`，包含：

- **执行摘要**：100 章验证结果（1 页）
- **修复清单**：Task 092-100c 的修复内容及效果
- **验证数据**：Ch2-Ch100 的完整指标表
- **问题清单**：未解决的问题及影响评估
- **可扩展性评估**：100 章 vs 200 章 vs 300 章
- **成本分析**：LLM 调用数、时间、费用
- **决策门 1 结论**：通过 / 有条件通过 / 不通过

### 3. 决策门 1 评估文档

生成 `docs/decision-gate-1.md`：

```markdown
# 决策门 1：Phase B 验收评估

## 日期：2026-06-XX

## 验收项

| # | 验收项 | 目标 | 实际 | 判定 |
|---|--------|------|------|------|
| 1 | 100 章全自动 | 0 失败 | ? | ? |
| 2 | 字数达标率 | > 65% | ? | ? |
| 3 | budget_used | < 1.3 平均, < 1.5 最大 | ? | ? |
| 4 | health_score | ≥ 3.0 | ? | ? |
| 5 | token_budget | < 1.3 平均, < 1.5 最大 | ? | ? |
| 6 | 0 中断 | 无人工干预 | ? | ? |

## 结论

□ 通过 — 所有验收项达标，Phase B 成功收尾
□ 有条件通过 — 核心项达标，次要项有已知限制
□ 不通过 — 核心项未达标，需要额外修复

## 下一步

| 情况 | 行动 |
|------|------|
| 通过 | 进入 V4.1（Prompt 优化 + 质量提升） |
| 有条件通过 | 记录限制，进入 V4.1（优先修复限制项） |
| 不通过 | 启动 Phase C（ContextService）评估 |
```

### 4. 更新 docs/INDEX.md

确保所有新文档被索引：
- `docs/v4-0-phase-b-report.md`
- `docs/decision-gate-1.md`
- `tasks/100a-revision-handler-floor-protection.md` 及 DONE
- `tasks/100b-quality-gate-and-edit-audit.md` 及 DONE
- `tasks/100c-context-pressure-optimization.md` 及 DONE

### 5. 归档数据

将验证数据归档到 `archive/projects/`：

```bash
archive/projects/
└── v4_0_phase_b_ch100/
    ├── test.db              # 完整数据库
    ├── progress.json        # 逐章指标
    ├── report.md            # 验证报告
    ├── lifecycle_report.md  # 生命周期趋势
    └── llm_calls.jsonl      # LLM 调用日志
```

### 6. Git Commit

```bash
git add -A
git commit -m "V4.0 Phase B: 100章验证完成 + 决策门1评估

- Task 092: Writer 字数预算分配
- Task 094: Health Score 公式修正 + Settlement 去重
- Task 095: 场景结构保护
- Task 096: Ch2-Ch50 回归验证
- Task 098: 上下文压力计 + Accept 守卫
- Task 099: Ch2-Ch50 重跑验证
- Task 100a: RevisionHandler 下限保护
- Task 100b: 流程质量门 + edit 审计
- Task 100c: 上下文压力优化
- Task 103: 文档交接 + 决策门1

验证结果：X章完成，Y%达标率，Z% budget"
```

---

## Out of Scope（明确不做）

- 代码修改
- 300 章验证
- Phase C（ContextService）实施

---

## 验收标准（Acceptance Criteria）

- [ ] `docs/STATUS.md` 更新 Phase B 结果
- [ ] `docs/v4-0-phase-b-report.md` 生成
- [ ] `docs/decision-gate-1.md` 生成
- [ ] `docs/INDEX.md` 更新
- [ ] 数据归档到 `archive/projects/v4_0_phase_b_ch100/`
- [ ] Git commit 提交
- [ ] `pytest -x -q` 全量通过
- [ ] 生成了 `tasks/103-v4-0-docs-handover-DONE.md`

---

## 参考

- `docs/STATUS.md`
- `docs/INDEX.md`
- `AGENTS.md`
- `tasks/091-phase-b-ch21-ch50-e2e-DONE.md`
- `evals/output/task_099_scifi_webnovel/report.md`

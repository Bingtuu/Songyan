# Task 131: 任务文档归档与状态一致性清理

> **类型**: 工程清理 / 文档维护  
> **日期**: 2026-06-26  
> **前置**: Task 120–130 已完成  
> **目标**: 消除过时规划稿与 DONE 文档并存的状态混乱，确保 `docs/STATUS.md`、`docs/INDEX.md`、`tasks/V5-README.md` 指向正确的最终事实文档。

---

## 1. 背景与问题

当前 `tasks/` 目录中存在两类状态不一致：

1. **规划稿与 DONE 文档并存**：
   - `tasks/122-v51-systematic-test-matrix.md` 仍显示"122c 部分完成、122d TODO"，但子任务已全部完成并有 `-DONE.md`。
   - `tasks/126-small-window-enforce-validation.md` 与 `-DONE.md` 内容大量重复。
   - `tasks/121d-ch1-ch150-single-run-rerun.md` 等早期任务规划稿仍留在根目录。

2. **索引文档指向不一致**：
   - `docs/INDEX.md` 中部分条目指向规划稿而非 `-DONE.md`（如 `121d-ch1-ch150-single-run-rerun.md`）。
   - `docs/STATUS.md` 中历史状态描述可能引用过时的 run_id 或任务状态。

这种状态混乱会导致新加入的开发者或代理读取到错误信息，降低文档可信度。

---

## 2. 清理原则（Brainstorming）

### 原则 A：最终事实优先
- 凡是有 `-DONE.md` 的任务，以 `-DONE.md` 为唯一最终状态依据。
- 无 `-DONE.md` 的规划稿若任务已实际完成，应补充 `-DONE.md` 或归档。

### 原则 B：规划稿可保留但应归档
- 已完成任务的历史规划稿有设计价值，不应直接删除。
- 应移入 `archive/tasks/` 或 `archive/v5/plans/`，避免与活跃任务混淆。

### 原则 C：索引只指向最终文档
- `docs/INDEX.md`、`docs/STATUS.md`、`tasks/V5-README.md` 中的链接应优先指向 `-DONE.md`。
- 明确标注"历史规划稿见 archive"。

### 原则 D：不做无根据的状态修改
- 不凭空把规划稿改成 DONE。
- 不删除尚未完成且仍在执行的规划稿。

---

## 3. 具体清理清单

### 3.1 已确认可归档的规划稿

| 文件 | 状态 | 操作 |
|------|------|------|
| `tasks/122-v51-systematic-test-matrix.md` | 子任务全部完成 | 移入 `archive/tasks/` 或标记为 DONE 并归档 |
| `tasks/126-small-window-enforce-validation.md` | 已有 `-DONE.md` | 移入 `archive/tasks/` |
| `tasks/121d-ch1-ch150-single-run-rerun.md` | 历史规划稿 | 移入 `archive/tasks/` |
| `tasks/113-ch101-convergence-settlement-blocker-fix.md` | 已有 `-DONE.md` | 移入 `archive/tasks/` 或确认是否已归档 |
| `tasks/111a-workflow-decision-contract-fix.md` | 已有 `-DONE.md` | 移入 `archive/tasks/` |
| `tasks/111b-settlement-state-integrity-fix.md` | 已有 `-DONE.md` | 移入 `archive/tasks/` |
| `tasks/111c-context-prompt-consistency-fix.md` | 已有 `-DONE.md` | 移入 `archive/tasks/` |
| `tasks/111d-quality-gate-settlement-blockers-fix.md` | 已有 `-DONE.md` | 移入 `archive/tasks/` |
| `tasks/111e-task112-reporting-dg2-gate-fix.md` | 已有 `-DONE.md` | 移入 `archive/tasks/` |
| `tasks/111f-context-snapshot-prompt-metadata-fix.md` | 已有 `-DONE.md` | 移入 `archive/tasks/` |
| `tasks/111g-long-run-performance-containment.md` | 已有 `-DONE.md` | 移入 `archive/tasks/` |
| `tasks/112-preflight-blocker-fix.md` | 已有 `-DONE.md` | 移入 `archive/tasks/` |

> 注：具体列表需要在执行前用 `ls tasks/*.md | grep -v DONE` 重新扫描确认。

### 3.2 索引文档修正

- [ ] `docs/INDEX.md`：
  - 所有指向规划稿的链接改为指向 `-DONE.md`。
  - 在文档末尾增加"历史规划稿归档入口"段落。
- [ ] `docs/STATUS.md`：
  - 检查"当前结论"表中引用的任务文档是否指向 DONE 版本。
  - 更新"下一步规划"段落，纳入 Task 127–132。
- [ ] `tasks/V5-README.md`：
  - 在"文档使用规则"段落中强调：规划稿已归档，状态以 `-DONE.md` 为准。
  - 更新 Task 121–126 的文档链接，全部指向 `-DONE.md`。

### 3.3 新增文档引用检查

- [ ] 运行链接检查脚本或手动 `grep` 确认 `docs/` 和 `tasks/` 中没有死链。
- [ ] 确认 `archive/v5/INDEX.md` 已正确记录归档文档位置。

---

## 4. 验收标准

### 4.1 文件系统
- [ ] `tasks/` 根目录下只保留：
  - 活跃未完成任务（无 DONE 且确实未完成）；
  - 已完成任务的 `-DONE.md`；
  - 新创建的任务规划稿（如 Task 127–131）。
- [ ] 历史规划稿已移入 `archive/tasks/`（或按项目约定位置）。

### 4.2 索引一致性
- [ ] `docs/INDEX.md` 中所有 V5 任务链接指向 `-DONE.md` 或新创建的任务规划稿。
- [ ] `docs/STATUS.md` 的"下一步规划"更新为 Task 127–132。
- [ ] `tasks/V5-README.md` 的"文档使用规则"和任务状态表反映最新归档策略。

### 4.3 回归验证
- [ ] 全量 pytest 通过（本任务不改代码，预期无影响）。
- [ ] `ruff check src/ tests/ scripts/` 通过。
- [ ] 手动抽查 5–10 个文档链接可正常打开。

---

## 5. 依赖关系

```
Task 120-129 已完成 ──┐
Task 130 决策完成 ────┤──► Task 131 文档归档与状态清理 ──┬──► Task 132 V5.1 验收
                     │                                  │
archive/ 目录已存在 ──┘                                  └──► 后续 V5.2 任务创建
```

---

## 6. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 误把未完成任务归档 | 丢失活跃工作上下文 | 归档前逐一核对 `-DONE.md` 是否存在 |
| 移动文件破坏 git 历史 | 难以追溯 | 使用 `git mv` 移动，保留历史 |
| 索引更新遗漏 | 死链或指向错误 | 使用 `grep` 扫描所有 `.md` 中的 `tasks/` 链接 |
| 文档状态与实际代码不一致 | 误导开发者 | 只改链接和状态描述，不改代码逻辑 |

---

## 7. 交付物

- `tasks/131-task-docs-archive-and-status-cleanup-DONE.md`
- 归档文件：`archive/tasks/` 下新增的历史规划稿
- 更新后的 `docs/INDEX.md`
- 更新后的 `docs/STATUS.md`
- 更新后的 `tasks/V5-README.md`
- 全量 pytest / ruff 通过记录

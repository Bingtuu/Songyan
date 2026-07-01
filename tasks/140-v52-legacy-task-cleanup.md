# Task 140：V5.2 遗留任务状态清理

> **类型**: 文档整理 / 状态收口
> **状态**: 已完成
> **前置**: Task 138p 已完成，V5.2 主干默认配置已提交。
> **依赖**: `tasks/V5-README.md`、`docs/INDEX.md`。

## 背景

V5-README 中还有几个任务处于“活跃/未收口/验收未通过”状态，但它们的实际工作已被后续任务覆盖：

- **Task 137**：设定回收闭环与 tracking 刷新机制（活跃，后续由 138a-138f 承接收口）。
- **Task 138g**：critical orphan 根因复核与最小收口（已执行未收口，后续转入 138m/138n/138o）。
- **Task 136**：V5.2 Ch1-Ch20 采集窗口跨项目验证（已完成但验收未通过，orphan 未减半；后续 138n/138o 已解决长窗口问题）。

这些任务继续标记为“活跃”会造成 V5.2 状态模糊。本任务负责在文档中明确它们已被覆盖，避免后续误判。

## 目标

清理 V5.2 遗留任务状态，明确它们已被后续任务覆盖/关闭。

## 验收标准

- [x] 在 `tasks/V5-README.md` 的任务表中：
   - Task 137 状态改为“已关闭；工作由 138a-138f 承接完成”。
   - Task 138g 状态改为“已关闭；路径转入 138m/138n/138o 并解决”。
   - Task 136 状态改为“已完成；当时验收未通过，但后续 138n/138o 已提供长窗口修复证据”。
- [x] 在对应任务文件（`tasks/137-setting-recycling-closed-loop.md`、`tasks/138g-critical-orphan-root-cause-review.md`、`tasks/136-v52-enforce-ch1-ch20-validation-DONE.md`）顶部追加说明，指出后续覆盖任务。
- [x] 保持 `tasks/137-setting-recycling-closed-loop.md` 和 `tasks/138g-critical-orphan-root-cause-review.md` 原文件名（138e 已说明 Task 137 不归档），仅更新状态说明。
- [x] 更新 `docs/INDEX.md`。
- [x] 本任务文件转 DONE。

## 实现步骤

1. **修改 `tasks/V5-README.md`**
   - 找到 Task 137/138g/136 所在行；
   - 更新状态和说明列；
   - 在顶部口径或总结论中说明“V5.2 所有活跃子任务已收口”。

2. **修改任务文件**
   - `tasks/137-setting-recycling-closed-loop.md`：在顶部 metadata 后添加“本任务保持活跃期间，工作已由 Task 138a-138f 完成并归档。”
   - `tasks/138g-critical-orphan-root-cause-review.md`：添加说明“本任务未单独收口，根因分析与修复由 Task 138m/138n/138o 完成。”
   - `tasks/136-v52-enforce-ch1-ch20-validation-DONE.md`：添加说明“本次验证 orphan 增长速率未达标，但后续 138n/138o 长窗口验证已证明问题收敛。”

3. **可选：重命名**
   - 如果项目惯例要求未 DONE 文件不能长期存在，可将 137/138g 重命名为 `-DONE.md`。鉴于 138e 明确“Task 137 不归档”，这里建议只更新说明、不重命名。

4. **验证**
   - `ruff check tasks/V5-README.md docs/INDEX.md`（如适用）；
   - 人工检查表格无 broken link。

## 不做的事

- 不修改这些任务的原始结论或数据；
- 不删除历史任务文件；
- 不开启新的技术实现。

## 风险与 Fallback

- **风险**：重命名 137/138g 文件会破坏其他文档的链接。
  - Fallback：保持原文件名，仅更新说明。

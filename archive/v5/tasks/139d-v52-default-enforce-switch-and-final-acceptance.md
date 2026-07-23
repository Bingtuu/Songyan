# Task 139d：V5.2 默认 gate_mode 切换为 enforce 与最终验收包交付

> **类型**: 配置切换 / 最终验收
> **状态**: 🔄 执行中（代码已落地；Task 139c Ch51-Ch82 已完成，Ch80 为 draft；Task 139h 已修复 Ch80 字数膨胀；Ch83-Ch150 续跑 `run-df933dbf` 已跑到 Ch107，待完成后重跑 Ch80 并交付验收包）
> **前置**: Task 139b 已完成；Task 139c 执行中。
> **依赖**: `songyan run` CLI 参数解析、`GateConfig` 默认值、`docs/STATUS.md`、`tasks/V5-README.md`。

## 背景

V5.2 的核心目标之一是 **默认启用 enforce 模式**。Task 130 已为 `songyan run` 暴露 `--gate-mode` 参数，但默认值仍为 `observe`。在 139b/c 证明 enforce 模式 Ch1-Ch150 可行后，本任务负责：

- 将 `songyan run` 的默认 `gate_mode` 从 `observe` 改为 `enforce`；
- 更新相关文档、help 文本、入口状态；
- 交付 V5.2 最终验收包。

## 目标

完成 V5.2 的最终收口：默认启用 enforce 模式，更新所有入口文档，交付验收包。

## 验收标准

- [x] 修改 CLI 默认参数：未指定 `--gate-mode` 时，`songyan run` 默认使用 `enforce`。
- [x] 更新 help 文本（`src/songyan/cli/main.py` 内 `--gate-mode` 说明）。
- [ ] 运行全量 `pytest tests/ -q`，确保默认切换无回归（≥ 2035 passed，1 xfailed）。
- [x] 运行 `ruff check src/ tests/` 通过。
- [x] 更新 `docs/STATUS.md`：当前阶段已同步为 139c 验证中 / 139d 代码已落地。
- [x] 更新 `tasks/V5-README.md`：已标记 139b 完成、139c 执行中、139d 代码已落地。
- [ ] 生成 V5.2 最终验收包文档 `archive/v5/reports/task-139d-v52-final-acceptance-package.md`，包含：
   - 138n/138o/138p 改动摘要；
   - 139b/c enforce Ch1-Ch150 验证结果；
   - 默认 enforce 切换说明；
   - 全量测试与 lint 结果。
- [x] 更新 `docs/INDEX.md`。
- [ ] 本任务文件转 DONE（待 139c 通过后）。

## 实现步骤

1. **修改默认 gate_mode**
   - 定位 `src/songyan/cli/commands/run.py` 或 `src/songyan/workflows/phase2_graph.py` 中 `gate_mode` 默认值；
   - 将默认值从 `"observe"` 改为 `"enforce"`。

2. **更新 help 文本**
   - 修改 `cli_help.txt` 中 `--gate-mode` 说明；
   - 检查 `docs/STATUS.md`、`tasks/V5-README.md` 是否有相关说明。

3. **回归验证**
   - `pytest tests/ -q`；
   - `ruff check src/ tests/`；
   - 运行一次 `songyan run --help` 确认默认值显示正确。

4. **更新文档**
   - `docs/STATUS.md`：当前阶段改为“V5.2 已完成，默认 enforce 模式启用”。
   - `tasks/V5-README.md`：
     - 更新顶部口径；
     - 在 V5.2 遗留项表格中将“enforce 模式默认启用”标记为 ✅；
     - 添加 139a/139b/139c/139d 行。
   - `docs/INDEX.md`：添加 139 系列任务和报告链接。

5. **生成验收包**
   - `archive/v5/reports/task-139d-v52-final-acceptance-package.md`。

## 不做的事

- 不删除 `observe` 模式（保留 `--gate-mode observe` 用于调试）；
- 不改硬门禁阈值（阈值调整在 139a 完成）；
- 不新增功能。

## 风险与 Fallback

- **风险**：默认 enforce 后，用户在新项目开局期可能因 QG false 被暂停。
  - Fallback：确保 Task 128 的 `degraded_accept` 逻辑已生效；若问题仍存在，可在 CLI 中增加 `--gate-mode` 提示。
- **风险**：默认切换导致既有集成测试失败。
  - Fallback：检查测试是否依赖 `observe` 默认值，更新测试显式指定 `--gate-mode observe` 或 `gate_mode="observe"`。

# Task 207: V10 收口与归档

> **阶段**: V10.5 收口
> **状态**: ✅ 完成
> **前置**: Task 189-206 已完成；Task 204/205/206 结构 spike 已单独提交
> **边界**: 文档治理 / 归档规划 / V11+ 登记；不改 runtime，不接 hard gate

---

## 目标

汇总 V10 Task 189-206 的完成证据，完成 V10 阶段收口、文档入口同步、归档规划与 V11 前置登记。Task 207 不启动新实验，不把 Task 197-206 的 report-only 信号接入 prompt、CED、five-gate、segment audit、T9 或任何 hard gate。

---

## 范围

- 汇总 V10.1 Ch200 口径与 harness、V10.2 跨体裁 Ch200、V10.3 优秀度信号包、V10.4 结构 spike 的验收事实。
- 生成 V10 closure report，标记 V10 全量闭环。
- 创建 `archive/v10/INDEX.md` 作为归档规划入口，不移动当前活跃任务文件。
- 同步 `AGENTS.md`、`docs/STATUS.md`、`tasks/V10-README.md`、`docs/INDEX.md`、`README.md`。
- 登记 V11+ 后续项：开源可用化、metrics Ch200 慢路径修复、评测工具次要清理、alias / 命名漂移策略、KG diff / FactTrack / Storyline Tree derived view 生产化候选。

---

## 不做范围

- 不重跑 Ch200，不生成新章节。
- 不修改 Writer / CreativeDirector / ContextManager / SettlementExtractor / gate。
- 不修改 CED / five-gate / segment audit / T9 口径。
- 不把优秀度信号、KG diff、FactTrack validity interval 或 Storyline Tree 接入 runtime / prompt / hard gate。
- 不做 V11 开源用户可用化实现；只登记入口和后续优先级。

---

## 验收

- `tasks/207-v10-closure-and-archive-DONE.md` 落盘。
- `archive/v10/reports/207-v10-closure-report.md` 落盘。
- `archive/v10/INDEX.md` 落盘并说明归档策略。
- 入口文档状态一致，V10 标记为完成并路由 V11。
- `git diff --check` 通过。

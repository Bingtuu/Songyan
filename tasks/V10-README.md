# V10 阶段总结

> V10 已完成并归档。本文保留阶段结论和追溯入口；单项任务书、DONE、报告和 JSON artifact 见 `archive/v10/INDEX.md`。

## 阶段结论

| 方向 | 结论 |
|------|------|
| Ch200 长窗口 | sci-fi baseline 已冻结；xuanhuan / wuxia / urban 均完成 Ch200 总验收 |
| 硬质量门 | 三体裁 Ch200 均 accepted=200、gap=0、failed=[]、five-gate PASS、segment audit PASS、T9=0 |
| 优秀度信号 | Task 196-203 完成，保持 report-only，不进 prompt、CED 或 hard gate |
| 结构 spike | Task 204 KG diff、Task 205 validity interval、Task 206 Storyline Tree 均完成，decision=`defer` |
| 收口归档 | Task 207 完成，V10 物理归档已执行 |
| 下一阶段 | V11 开源可用化收尾，入口 `tasks/V11-Plan.md` |

## 验收分组

| 组 | 目标 | 状态 | 证据入口 |
|----|------|:----:|----------|
| A | Ch200 口径与工具 | ✅ | `archive/v10/tasks/189-ch200-baseline-and-checkpoints-DONE.md`、`archive/v10/tasks/191-ch200-harness-preparation-DONE.md` |
| B | 跨体裁 Ch200 | ✅ | `archive/v10/tasks/195-cross-genre-ch200-acceptance-DONE.md` |
| C | 优秀度信号包 | ✅ | `archive/v10/reports/203-excellence-integrated-report.md` |
| D | 结构升级 spike | ✅ | `archive/v10/reports/204-kg-diff-spike-report.md`、`archive/v10/reports/205-facttrack-validity-interval-report.md`、`archive/v10/reports/206-storyline-tree-spike-report.md` |
| E | 守护项 | ✅ | `archive/v10/reports/207-v10-closure-report.md` |

## 关键 artifact

| 类型 | 路径 |
|------|------|
| sci-fi Ch200 baseline | `archive/v10/artifacts/189-scifi-ch200-baseline.json` |
| Task 196 样本与标注 | `archive/v10/artifacts/196-excellence-sample-set.json`、`archive/v10/artifacts/196-excellence-annotations.json` |
| 优秀度整合 JSON | `archive/v10/artifacts/203-excellence-integrated-report.json` |
| KG diff manifest/report | `archive/v10/artifacts/204-kg-diff-sample-manifest.json`、`archive/v10/artifacts/204-kg-diff-spike-report.json` |
| FactTrack / Storyline Tree reports | `archive/v10/artifacts/205-facttrack-validity-interval-report.json`、`archive/v10/artifacts/206-storyline-tree-spike-report.json` |

## 仍需保留的边界

- Task 197-203 的优秀度信号只做观察和报告，不作为 hard gate。
- Task 204-206 是结构 spike，不是生产能力。
- CED 仍只使用 consistency-only、merged/source、正文证据口径。
- T9 仍是硬红线，不接受解释性豁免。
- KG diff / FactTrack / Storyline Tree 若要进入生产链路，必须另立 V11+ 任务并补回归证据。

## V11 路由

V11 不继续扩张生成能力，优先做开源用户可用化：

- 安装与本地环境自检。
- `.env` 与配置安全。
- `songyan doctor` 诊断增强。
- `create-project` 外部用户路径。
- 导出、报告、备份/恢复与失败恢复。
- Release checklist 和 README/Quickstart 校准。

执行入口：`tasks/V11-Plan.md`。建议首任务为 Task 208 readiness audit。

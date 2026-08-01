# V10 Closure Report

> **Task**: 207 V10 收口与归档
> **状态**: V10 全量闭环
> **完成时间**: 2026-08-01
> **入口**: `tasks/V10-README.md`

---

## 总结

V10 已完成。阶段目标“跨体裁 Ch200 + 优秀度信号包 + 结构升级 spike”全部闭环，且没有把 report-only 信号接入生成链路、CED、five-gate、segment audit、T9 或 hard gate。

V10 的主结论：

- Ch200：sci-fi baseline 冻结，xuanhuan / wuxia / urban 三个非 sci-fi 体裁均达到 Ch200，三体裁均 accepted=200、gap=0、failed=[]、five-gate PASS、segment audit PASS、T9 hard hits=0。
- 优秀度：Task 196-203 完成离线 report-only 信号包，从校准样本、结构/AI 腔、style card、角色声纹、judge 偏差、可读性到统一报告整合均可追溯。
- 结构升级：Task 204/205/206 完成 KG diff、FactTrack validity interval、Storyline Tree 三个 shadow spike，三者共同结论为 defer：信号有效，但生产化需要 alias policy、derived view、历史 backfill 与更强结构标注，V10 内不得接 runtime 或 hard gate。

---

## V10.1 口径与工具

| Task | 结论 | 入口 |
|------|------|------|
| 189 | sci-fi Ch200 baseline/checkpoint 冻结；Ch125/150/175/200 baseline 可重放 | `tasks/189-ch200-baseline-and-checkpoints-DONE.md` |
| 190 | Ch100 终点事实源盘点完成，建立三态准入 | `tasks/190-ch100-terminal-source-inventory-DONE.md` |
| 191 | Ch200 harness 完成，固定 DB/project/run/audit 路径和三态准入 | `tasks/191-ch200-harness-preparation-DONE.md` |

冻结 baseline：`tasks/189-scifi-ch200-baseline.json`。

---

## V10.2 跨体裁 Ch200

| 体裁 | 结果 | 入口 |
|------|------|------|
| xuanhuan | Ch200 completed，five-gate PASS，segment audit PASS，T9=0 | `tasks/192-xuanhuan-ch200-climb-DONE.md` |
| wuxia | Ch200 completed，five-gate PASS，segment audit PASS，T9=0 | `tasks/193-wuxia-ch200-climb-DONE.md` |
| urban | Ch200 completed，five-gate PASS，segment audit PASS，T9=0；Ch199/200 使用 fallback model，已记录限制 | `tasks/194-urban-ch200-climb-DONE.md` |
| cross-genre | 三体裁总验收通过 | `tasks/195-cross-genre-ch200-acceptance-DONE.md` |

Ch200 hard gate 仍只引用 accepted head、five-gate、segment audit、T9 与 Task 189 baseline，不混入优秀度或结构 spike 信号。

---

## V10.3 优秀度信号包

| Task | 产物 | 结论 |
|------|------|------|
| 196 | `tasks/196-excellence-sample-set.json` / annotations / calibration report | anchor + spotcheck agent-deep-read 为唯一校准真值，prelabel 仅低置信对照 |
| 197/198 | `tasks/197-198-excellence-signals-report.json` | 结构同质化与中文 AI 腔 report-only 信号落地 |
| 199 | `tasks/199-style-card-report.json` | style card 仅为观察画像，不注入 prompt |
| 200 | `tasks/200-character-voice-anchor-report.json` | 角色声纹锚点保留 unknown 归因，不写回角色档案 |
| 201 | `tasks/201-judge-bias-report.json` | judge 偏差与对策协议离线落地，不调用 LLM |
| 202 | `tasks/202-readability-feasibility-report.json` | 真实 PPL defer，可读性 proxy 仅 report-only |
| 203 | `tasks/203-excellence-integrated-report.json` | 统一优秀度报告双视图落地，不生成硬分、排名或 PASS/FAIL |

Task 203 汇总数据：source artifacts=7、chapter view=60、signal view=50、signal layers=6。

---

## V10.4 结构升级 Spike

| Task | 样本 | 结果 | 决策 |
|------|------|------|------|
| 204 KG diff | 6 positive + 3 negative | positive 6/6 高置信复现，negative 3/3 无高置信误报 | defer |
| 205 FactTrack validity interval | 复用 Task 204 样本 | interval_explained=6，false_positive=0 | defer |
| 206 Storyline Tree | 复用 Task 204/205 样本 | needs_storyline_tree=3，tree_explained=5，false_positive=0 | defer |

共同结论：三类结构信号有诊断价值，但 V10 不接 runtime，不改 schema，不接 hard gate。后续如生产化，优先考虑 report-only derived view + alias policy + validity interval + storyline fact links 的组合方案。

---

## Report-Only 边界复核

- 优秀度信号未进入 CED。
- 优秀度信号未进入 Writer / CreativeDirector prompt。
- KG diff / FactTrack validity interval / Storyline Tree 未进入 runtime、prompt 或 hard gate。
- CED 仍保持 consistency-only、merged/source、正文证据口径。
- Ch200 终判仍只引用 accepted/five-gate/segment audit/T9。
- T9 仍为硬红线，不接受解释性豁免。

---

## 归档策略

`archive/v10/INDEX.md` 已建立为 V10 归档规划入口。当前不移动 `tasks/` 与 `docs/reports/` 中的活跃 V10 产物，避免破坏现有引用；后续若执行物理归档，按 `archive/v10/INDEX.md` 中的路径计划迁移，并同步 `AGENTS.md`、`docs/STATUS.md`、`docs/INDEX.md` 与 `tasks/V10-README.md`。

---

## V11+ 登记

V11 主方向：开源可用化收尾，入口 `tasks/V11-Plan.md`。

后续登记项：

- metrics Ch200 慢路径修复：`songyan metrics --chapters 1-200` 历史库慢路径曾超过可接受等待时间，不作为 V10 hard gate 失败。
- 评测工具次要清理：baseline `min_up_to` 字段未消费、five_gate `final>=100` 过时语义、harness inventory 的 DONE markdown 正则兜底、`_genre_from_db_path` 文件名反推、`DATABASE_URL cleanup` 提示误导、`_create_v10_project_run` 裸写 repository 评估。
- alias / 命名漂移策略：承接 Task 193.s/v 与 Task 204-206 的共同遗留。
- KG diff / FactTrack / Storyline Tree 生产化候选：仅作为 V11+ derived report view 或诊断 bundle 的候选，不直接接 hard gate。
- V11 外部用户路径：doctor、backup/restore、run bundle、配置安全、Quickstart、release checklist。

---

## 验证

Task 207 为文档-only 收口，不改代码、不改 runtime。验证命令：

```powershell
git diff --check
```

通过后，V10 可标记为全量闭环。

# Songyan Documentation

地图只列当前要读的文档。历史材料在 [archive/](archive/README.md)，**日常不要加载**。

## 当前

| Document | Purpose |
|----------|---------|
| [AGENTS.md](../AGENTS.md) | 冷启动规则：产品方向、文档权威、书面接受前不写代码 |
| [V1.0 PRD](prd-v1.md) | 产品权威。两条主路径、W0–W6、里程碑 M0–M4。Owner 已接受这轮文档 |
| [M0 技术方案](tech-m0.md) | 只读工作台。步 1–4 已进 `main`；§6–7 代码验收 PASS（`80f4107`） |
| [M1 技术方案](tech-m1.md) | 人确认入典 + 规则 `check`。**已接受**（Mew 拍板）；步 1–5 已进 `main`；§6–7 代码验收 PASS（`69d7ece`） |
| [M2 技术方案](tech-m2.md) | 硬事实标脏 + 承诺债务 + 抽取提案。**已接受**（2026-11-04；B1–B6 原样）；步 1–6 已在 `main`；§6–7 代码验收 PASS（证据 tip `f1c3093`） |
| [M3 技术方案](tech-m3.md) | 章内 Variant / 抽卡。**已接受**（2026-11-06；t104s937；B1–B7 原样）；步 1–3 已合入；步 4 编码进行中 |
| [ADR-0001](adr/0001-plan-first-facts.md) | 事实写入方向。阶段 A–C 已关闭，不重开召回 KPI |
| [STATUS](STATUS.md) | 工程事实：包仍是 0.5.0；M0 / M1 / M2 代码验收 PASS；tech-m3 **已接受**；M3 步 1–3 已合入；步 4 进行中 |
| [HANDOFF](HANDOFF-mew.md) | 当天下一步：M3 步 4（`variant pick`/`abandon`）；合入后再授权步 5 |
| [Quickstart](quickstart.md) | 安装、配置、短窗口、导出 |
| [Troubleshooting](troubleshooting.md) | 失败恢复 |
| [Release Checklist](release-checklist.md) | 维护者发布门 |
| [质量门方法论](quality-gates.md) | CED / T9 / 五门口径 |

## 不要默认加载

[docs/archive/](archive/README.md)：旧自动成书任务圣经、技术参考、V13–V15 路线、plan-first 全文、实验章节正文，以及 2026-10-26 的 AGENTS / STATUS / PRD 副本。

旧路径 [prd-v1-writing-assist.md](prd-v1-writing-assist.md) 只留指针，指向 [prd-v1.md](prd-v1.md)。

Plan-first 的短指针仍在 [ROADMAP-plan-first.md](ROADMAP-plan-first.md)（**CLOSED**）。打开它不会带出全文。

## 运行时不要提交

`songyan.db`、`*.db`、`logs/`、`exports/`、`backups/`、`bundles/`、`.env`。

需要脱敏诊断包时用 `songyan bundle-run --run-id <run_id> --output bundles/`。

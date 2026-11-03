# Songyan Documentation

地图只列当前要读的文档。历史材料在 [archive/](archive/README.md)，**日常不要加载**。

## 当前

| Document | Purpose |
|----------|---------|
| [AGENTS.md](../AGENTS.md) | 冷启动规则：产品方向、文档权威、书面接受前不写代码 |
| [V1.0 PRD](prd-v1.md) | 产品权威。两条主路径、W0–W6、里程碑 M0–M4。Owner 已接受这轮文档 |
| [M0 技术方案](tech-m0.md) | 只读工作台。步 1–4 已进 `main`；整里程碑验收见 §6–7 |
| [ADR-0001](adr/0001-plan-first-facts.md) | 事实写入方向。阶段 A–C 已关闭，不重开召回 KPI |
| [STATUS](STATUS.md) | 工程事实：包仍是 0.5.0；M0 步 1–4 已在 `main` |
| [HANDOFF](HANDOFF-mew.md) | 当天下一步：M0 验收或 owner 决定 confirm / M1 |
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

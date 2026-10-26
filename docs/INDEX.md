# Songyan Documentation

地图只列当前要读的文档。历史材料在 [archive/](archive/README.md)，**日常不要加载**。

## 当前

| Document | Purpose |
|----------|---------|
| [AGENTS.md](../AGENTS.md) | 代理与贡献者规则：现在是什么、不要读什么 |
| [V1.0 写作助手 PRD](prd-v1-writing-assist.md) | 产品权威。工作流 W0–W6。实现等 owner 接受 |
| [ADR-0001](adr/0001-plan-first-facts.md) | 事实写入方向。阶段 A–C 已关闭，不重开召回 KPI |
| [STATUS](STATUS.md) | 工程事实：v0.5 能做什么；Ch1–10 管线过、文学不过 |
| [HANDOFF](HANDOFF-mew.md) | 当天下一步 |
| [Quickstart](quickstart.md) | 安装、配置、短窗口、导出 |
| [Troubleshooting](troubleshooting.md) | 失败恢复 |
| [Release Checklist](release-checklist.md) | 维护者发布门 |
| [质量门方法论](quality-gates.md) | CED / T9 / 五门口径 |

## 不要默认加载

[docs/archive/](archive/README.md)：旧自动成书任务圣经、技术参考、V13–V15 路线、plan-first 全文、实验章节正文。

Plan-first 的短指针仍在 [ROADMAP-plan-first.md](ROADMAP-plan-first.md)（**CLOSED**）。打开它不会带出全文。

## 运行时不要提交

`songyan.db`、`*.db`、`logs/`、`exports/`、`backups/`、`bundles/`、`.env`。

需要脱敏诊断包时用 `songyan bundle-run --run-id <run_id> --output bundles/`。

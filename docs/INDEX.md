# Songyan Documentation

Public documentation map for users and contributors.

## Start Here

| Document | Purpose |
|----------|---------|
| [README](../README.md) | Project overview, features and shortest path |
| [Status](STATUS.md) | Current release readiness and known limits |
| [Quickstart](quickstart.md) | Install, configure, run and export |
| [Troubleshooting](troubleshooting.md) | Common failures and recovery commands |

## Release and Contribution

| Document | Purpose |
|----------|---------|
| [Release Checklist](release-checklist.md) | Maintainer release gate and smoke commands |
| [Minimal Reproduction Guide](minimal-repro.md) | How to file actionable issues |
| [Contributing](../CONTRIBUTING.md) | Contribution workflow and project boundaries |
| [Changelog](../CHANGELOG.md) | Release notes |
| [License](../LICENSE) | AGPL-3.0 license |

## Quality Methodology

| Document | Purpose |
|----------|---------|
| [质量门方法论：CED / T9 / 五门](quality-gates.md) | 质量度量口径定义、证据要求、阈值出处与复现命令 |
| [Ch200 baseline 结果摘要](baseline-results.md) | 4 体裁 200 章验收的公开聚合数值（已脱敏） |

## Roadmap

| Document | Purpose |
|----------|---------|
| [V13 质量方法论公开化](roadmap/v13-quality-methodology.md) | 公开 CED / T9 / 五门口径与脱敏 baseline（已规划，Task 226-229） |
| [V14 成本与按角色模型路由](roadmap/v14-model-routing.md) | per-role LLM 配置与成本拆分（已规划，Task 230-233） |
| [V15 导入已有小说续写](roadmap/v15-import-continue.md) | ingest → segment → replay → synthesize → publish（进行中，Task 234/235/236/237 DONE） |
| [Plan-first 一致性路线](ROADMAP-plan-first.md) | 约 90 天证明跨章真错误召回；阶段 A/B/C 与非目标 |
| [V1.0 写作助手 PRD](prd-v1-writing-assist.md) | 人主导写作助手的规划；实现等 owner 接受本文之后 |
| [ADR-0001 Plan-first 事实层](adr/0001-plan-first-facts.md) | 计划写 canon，正文对照计划做窄检查 |
| [Mew 每日切片](HANDOFF-mew.md) | 下一刀、相关代码位置、报告格式 |

## Architecture References

| Document | Purpose |
|----------|---------|
| [Engineering Notes](architecture/04-vibe-coding-engineering.md) | Engineering model and workflow notes |
| [Technical Reference](architecture/05-tech-reference.md) | Technical reference for deeper contributors |

## Runtime Artifacts

Songyan creates local runtime artifacts that should not be committed:

- `songyan.db`, `*.db`, `*.sqlite`
- `logs/`
- `exports/`
- `backups/`
- `bundles/`
- `.env`

Use `songyan bundle-run --run-id <run_id> --output bundles/` when you need a redacted diagnostic package for issue reports.

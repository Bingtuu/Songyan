<div align="center">
  <img src="docs/icon/logo02.png" alt="Songyan logo" width="148" />

  <h1>Songyan（松烟）</h1>

  <p><strong>基于 LangGraph 的多 Agent 中文长篇小说写作系统</strong></p>
  <p>本地优先的 Python CLI：人维护事实圣经，模型按圣经写正文。</p>
  <p><em>A local-first, multi-agent system for writing long Chinese fiction.</em></p>

  <p>
    <img src="https://img.shields.io/badge/version-v0.5-2f6f4e" alt="v0.5" />
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-%3E%3D3.11-blue" alt="Python >= 3.11" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue" alt="License AGPL-3.0" /></a>
    <a href="https://github.com/Bingtuu/Songyan/actions/workflows/ci.yml"><img src="https://github.com/Bingtuu/Songyan/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
    <img src="https://img.shields.io/badge/storage-SQLite-044a64" alt="SQLite" />
    <img src="https://img.shields.io/badge/interface-CLI-222222" alt="CLI" />
  </p>
</div>

---

**v0.5**（包版本 `0.5.0`）是可用预览。已核对的生成证据是科幻模板上的真实模型前三章。十章及以上的正式长跑还没有在这个 tip 上验收。

## 这是什么

Songyan 把中文长篇创作收成一条可恢复、可审计的本地流水线。编排在 LangGraph 上。长期事实放在 SQLite。模型写正文；Songyan 负责本章上下文、审查、版本、失败恢复和诊断。

单章大致是：

```text
规划 → 组装上下文（含本章已批准计划卡）→ 生成初稿
    → 规则 / 语义 / 文学审查 → 修订 → 接收
    → SettlementExtractor 写入原结算库
```

它是命令行程序，面向能配置 LLM API key 的技术用户。内置模板包括 `scifi`、`xuanhuan`、`wuxia`、`urban`、`urban_fantasy`、`post_apocalyptic`、`mystery_noir`。

## 为什么

长篇的难点是写到后面仍对得上前面已经成立的事实：人物、物件、时间、已经付过的代价。开放式「从正文里把事实抽出来，再当成下一章的权威」会把漂移吸进事实库。

因此当前方向是 [ADR-0001](docs/adr/0001-plan-first-facts.md)：权威事实由计划层和人写入，正文对照已批准的计划卡做窄检查。路线与阶段记录在 [Plan-first 路线](docs/ROADMAP-plan-first.md)。

### 计划卡是本章事实圣经

v0.5 采用薄封装，Phase A–C 已在 main 上收束：

- 已批准的计划卡是本章事实圣经。写作和修订把它放在上下文最前面。待审卡、别的章、别的项目不进这段圣经。
- 审查会从本章正文读出类型化摘录和主张锚，交给同一扇只读门。门没过时，失败出现在 human gate，并记在日志里。
- 人批准仍是进入 plan canon 的入口。
- `SettlementExtractor` 仍只写原来的结算库。抽取结果不会自动写成 plan canon。

Phase C 的第二体裁是都市灵异《末班铜牌》。活路径召回 **1/5**（门槛 ≥4/5），退出条件没有满足。Owner Bingtuu 于 2026-10-26 接受的操作结论是：**人维护事实圣经，AI 按圣经写。** 阶段 B 的霞飞路活路径召回 5/5 另有记录。细节、成本和人工口径在 [HANDOFF](docs/HANDOFF-mew.md)，不在这里展开。

## 安装

- Python 3.11+
- 兼容 OpenAI 接口的 LLM endpoint。仓库里的默认示例是 DeepSeek。
- 一块可写的本地目录，用来放 SQLite、日志和导出文件。

开发安装：

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

在 bash 里把复制那一行换成 `cp .env.example .env`。其余 `songyan` 子命令相同。

`.env` 至少要有：

```dotenv
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
DATABASE_URL=sqlite:///songyan.db
CHECKPOINTER_MODE=sqlite
```

Windows 上做短窗口验证、遇到 checkpoint 文件锁时，可以临时使用 `CHECKPOINTER_MODE=memory`。按角色拆模型、成本口径，以及为什么不要把带思考链的 reasoning 模型配给写作角色，见 [Quickstart](docs/quickstart.md)。

报告里的 chat 成本估算按 owner 口径标注：输入 **¥2/M**，输出 **¥8/M**。这是估算标签，不是供应商账单。这些跑次里记下的单章停线是 **¥7.66**（早前 v1 第 3 章 ¥0.766 的十倍）。它是实验和冒烟记录里的停线，由人掌握；可选的 `SONGYAN_RUN_COST_BUDGET` 是另一套运行预算，见 Quickstart。

## 快速开始

下面是最短闭环。逐步说明、失败恢复和导出细节在 [Quickstart](docs/quickstart.md)。

```powershell
songyan doctor --init-db
songyan create-project --template scifi
songyan run --project-id <project_id> --chapters 1-3 --auto-confirm
songyan report --run-id <run_id>
songyan export --project-id <project_id> --chapters 1-3 --format md --output exports/
```

`create-project` 会打印 `project_id`，`run` 会打印 `run_id`。真实生成会消耗 API 额度。前三章在 2026-10-26 那次通过的冒烟上，owner 口径合计 ¥1.035，最贵的一章约 ¥0.400。

常用命令：

| 命令 | 作用 |
|------|------|
| `songyan doctor --init-db` | 检查环境并初始化 / 迁移 SQLite |
| `songyan create-project --template <id>` | 从内置模板建项 |
| `songyan list-projects` | 列出本地项目 |
| `songyan run --project-id <id> --chapters 1-3 --auto-confirm` | 跑短窗口 |
| `songyan report --run-id <run_id>` | 从 run log 生成报告 |
| `songyan bundle-run --run-id <run_id> --output bundles/` | 生成脱敏诊断包 |
| `songyan export --project-id <id> --format md --output exports/` | 导出 accepted 正文 |
| `songyan backup` / `songyan restore` | 备份与恢复项目资产 |
| `songyan profile validate` / `history` / `rollback` | 校验、查看和回滚体裁 profile |
| `songyan five-gate` / `songyan t9` | 只读重算质量门口径 |
| `songyan import ...` | 导入已有小说；真实书稿续写仍未验收，见下方限制 |

## v0.5 现在到哪

Owner 把当前 tip 命名为 **v0.5**。安装元数据是 **`0.5.0`**（`pyproject.toml` 与 `songyan.__version__`）。git tag 由维护者在合并并通过 CI 之后处理。

按 [Quickstart](docs/quickstart.md) 可以安装、自检和建项。这个 tip 上核对过的真实生成，是下面这一次科幻前三章。冒烟跑在 main `eaa6bef`（PR #20：正文里已经写出的主角决策会写回摘要，不再因此误入 `settlement_review`）上，由随后的文档提交 `58d3621`（PR #21）记入 main：

| 项 | 记录 |
|----|------|
| 日期 | 2026-10-26（Asia/Shanghai） |
| 代码 | `eaa6bef7721e43ccd1b53be2280076a355842d9b` |
| 项目 | `5a7f3a4263bc499d95109ea460aa79df`（`scifi` 模板，标题《轨道蜃景》） |
| 运行 | `run-552b2c04`，退出码 0，`status=completed` |
| 章节 | Ch1–3 全部 accepted |
| 结算 | 没有 `settlement_review` 或 missing_facts 失败 |
| 上下文 | ContextEmergency 只有连续警告，没有 AutoHalt |
| 成本 | owner 口径合计 ¥1.035（输入 ¥2/M、输出 ¥8/M）；单章最高约 ¥0.400；停线 ¥7.66 没有碰到 |

更早一次同口径冒烟在 `11c4c761`（PR #19）上失败：只有第 1 章 accepted，第 2、3 章卡在 `settlement_review`。那次留下作历史，不抹掉。书稿、数据库和日志不在本仓库；维护者 box 上的路径只写在 [HANDOFF](docs/HANDOFF-mew.md)。发布项如何复核，见 [Release Checklist](docs/release-checklist.md)。公开状态板是 [STATUS](docs/STATUS.md)。

更早的内部长窗口（2026-08 冻结的科幻、玄幻、武侠、都市各 200 章 accepted）是另一份历史证据，公开聚合在 [baseline 摘要](docs/baseline-results.md)。它不能代替 v0.5 这个 tip 上的长跑验收。

## 已知限制

- 十章及以上的正式长跑还没有在这个 tip 上验收。v0.5 的生成证据停在前三章。
- 都市灵异活路径没有过召回退出条件。跨章事实仍要人维护圣经；模型负责按卡写，并接受窄检查。
- `SettlementExtractor` 继续写结算库。plan canon 只来自已批准的计划卡；抽取行不会被自动批准进去。
- `songyan import` 的自动化测试和 CLI 冒烟已有，真实书稿导入后再续写的验收还没有。导入后续写质量先按未验证对待。
- 需要自备 API key，生成会花钱。报告里的人民币数字是 owner 口径估算。
- 带思考链的 reasoning 模型不适合写作角色：思考链会占满该调用的输出预算，正文可能为空并被质量门拦住。
- 研究 / report-only 信号不进入 runtime prompt、CED、T9 或 hard gate。
- 不要提交 `.env`、API key、私密书稿、本地数据库、未脱敏日志、backup 或 bundle。失败报告优先用 `songyan bundle-run`。

## 文档

| 文档 | 何时去看 |
|------|----------|
| [Quickstart](docs/quickstart.md) | 安装、配置、短窗口、报告和导出 |
| [STATUS](docs/STATUS.md) | 现在什么能用、冒烟证据和限制 |
| [Release Checklist](docs/release-checklist.md) | 维护者发布门槛和冒烟口径 |
| [HANDOFF](docs/HANDOFF-mew.md) | 每日切片、下一刀、box 上的证据路径 |
| [ADR-0001](docs/adr/0001-plan-first-facts.md) | 为什么权威事实从计划层来 |
| [Plan-first 路线](docs/ROADMAP-plan-first.md) | 阶段 A–C 与非目标 |
| [Troubleshooting](docs/troubleshooting.md) | 常见失败和恢复命令 |
| [质量门](docs/quality-gates.md) | CED / T9 / 五门的口径 |
| [Changelog](CHANGELOG.md) | 版本记录 |
| [文档索引](docs/INDEX.md) | 公开文档地图 |

## 参与贡献

贡献方式、测试命令和工程边界在 [CONTRIBUTING](CONTRIBUTING.md)。提问题前先看 [最小复现指南](docs/minimal-repro.md)。

几条不会在普通 PR 里放宽的边界：

- SQLite 是长期事实库。章节版本只追加，不覆盖历史。
- Agent 不直接拿数据库连接写权威行；写入走 repository / service。
- 长 prompt 放在包内的 prompt cards 里。
- 未批准的抽取结果不能被下一章当成已成立的 plan canon。

## 许可证

Songyan 使用 [AGPL-3.0](LICENSE)。

<div align="center">
  <img src="docs/icon/logo02.png" alt="Songyan logo" width="148" />

  <h1>Songyan（松烟）</h1>

  <p><strong>基于 LangGraph 的多 Agent 中文长篇小说写作系统</strong></p>
  <p>你先批准这一章的剧情事实，模型按这些事实写正文，审查负责抓住写偏的地方。</p>
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

## 目标

长篇难在写到后面，还对得上前面已经成立的事。Songyan 把这件事做成一条跑在本机上的流水线：多个 Agent 在 LangGraph 上分工，长期记录放在 SQLite。

- **计划卡由你批准。** 这一章的人物、物件、时间和已经发生的事，以这张卡为准。
- **模型按卡写正文。** 写出来的章节要和这些事实一致。
- **审查对照计划卡。** 正文写偏了会被标出来，再进入修订和接收。

草稿、修订和已接收的版本都留着，不覆盖旧稿。这是命令行工具，适合能自己配置模型 API key 的人。

## 结构

一章大致这样走：

```text
规划 → 把本章已批准的计划卡放进上下文 → 写初稿
    → 规则 / 语义 / 文学审查 → 修订 → 接收
    → 抽出的细节记入结算库
```

计划卡只服务当前这一章。还没批准的卡、别的章、别的项目不会混进来。从正文抽出的细节另外记在结算库里；已经批准的计划卡保持原样。

| 路径 | 作用 |
|------|------|
| `src/songyan/workflows/` | 章节编排 |
| `src/songyan/agents/` | 规划、写作、审查、修订、结算 |
| `src/songyan/plan_facts/` | 已批准的计划卡 |
| `src/songyan/db/` | SQLite 的表和读写 |
| `src/songyan/cli/` | `songyan` 命令 |
| `src/songyan/genres/`、`src/songyan/project_templates/` | 体裁配置和建项模板 |
| `src/songyan/prompts/` | 提示词卡片 |
| `docs/` | 使用说明和发布文档 |

设计取舍见 [ADR-0001](docs/adr/0001-plan-first-facts.md)，阶段说明见 [Plan-first 路线](docs/ROADMAP-plan-first.md)。

## 使用方式

需要 Python 3.11+、一个兼容 OpenAI 接口的模型服务（示例是 DeepSeek），以及一块可写的本地目录。

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

bash 里把复制换成 `cp .env.example .env`。在 `.env` 里填上 API key、接口地址、模型名和数据库路径。按角色换模型，以及为什么写作角色不要用带思考链的模型，见 [Quickstart](docs/quickstart.md)。

跑通前三章：

```powershell
songyan doctor --init-db
songyan create-project --template scifi
songyan run --project-id <project_id> --chapters 1-3 --auto-confirm
songyan report --run-id <run_id>
songyan export --project-id <project_id> --chapters 1-3 --format md --output exports/
```

`create-project` 会打印 `project_id`，`run` 会打印 `run_id`。模板还有 `xuanhuan`、`wuxia`、`urban` 等。备份、导入已有小说、质量门和排错都在 [Quickstart](docs/quickstart.md)。

报告里的费用按这个口径估算：输入 **¥2/M**，输出 **¥8/M**，单章停线 **¥7.66**。这是估算，不是供应商账单。

## 进展

**v0.5**（包版本 `0.5.0`）是技术预览。当前这条线上，科幻模板的真实模型前三章已经跑通。十章以及更长的连载，还没有作为这一版的验收标准。

把现成书稿导入后再接着写，自动化测试已经有了；用真实书稿续写，还没有验收。

证据和发布门槛见 [STATUS](docs/STATUS.md) 与 [Release Checklist](docs/release-checklist.md)。更早的长窗口公开数字在 [baseline 摘要](docs/baseline-results.md)。

## 文档

| 文档 | 何时去看 |
|------|----------|
| [Quickstart](docs/quickstart.md) | 安装、配置、短窗口、导出 |
| [STATUS](docs/STATUS.md) | 现在能用什么，以及限制 |
| [Release Checklist](docs/release-checklist.md) | 发布前要核对的项 |
| [baseline 摘要](docs/baseline-results.md) | 更早长窗口的公开数字 |
| [Troubleshooting](docs/troubleshooting.md) | 失败了怎么恢复 |
| [Changelog](CHANGELOG.md) | 版本记录 |
| [文档索引](docs/INDEX.md) | 其余公开文档 |

## 参与贡献

贡献方式、测试命令和工程边界见 [CONTRIBUTING](CONTRIBUTING.md)。提问题前先看 [最小复现指南](docs/minimal-repro.md)。不要提交 `.env`、API key、书稿、本地数据库或未脱敏日志；需要附诊断时用 `songyan bundle-run`。

## 许可证

Songyan 使用 [AGPL-3.0](LICENSE)。

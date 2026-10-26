# AGENTS.md

给在本仓库里改代码或改文档的人或代理。先读本文件，再读当前任务。不要把 `docs/archive/` 收进默认上下文。

## 现在是什么

Songyan（松烟）是 **人主导的连载写作助手**，外加一份结构化 **Canon**（已确认的事实）。人定方向和终稿；程序出草稿、记账、做窄检查。

当前可运行的包是 **v0.5**（`pyproject.toml` 里的 `0.5.0`）。「V1.0」只是下一产品代际的名字，不是版本号，也不要打 `v1.0` 标签。实现以 [docs/prd-v1-writing-assist.md](docs/prd-v1-writing-assist.md) 为准，而且要等 owner 接受该文之后。

已经关掉的事：plan-first 阶段 A–C（薄封装）。[ADR-0001](docs/adr/0001-plan-first-facts.md) 的方向还在：人维护事实圣经，模型按圣经写。不要重开题材检查器召回 KPI。

## 现在不是什么

- 不是无人值守写完一本小说的产品。`songyan run --chapters 1-N --auto-confirm` 是引擎 / 冒烟 / 长窗实验，不是作者主路径。
- 不是纯设定台账。写作辅助留在产品里。
- 不会静默改 Canon。抽取、结算摘要、审读建议默认是提案，不是事实。
- 不拥有文学质量。Ch1–10（`47954cb`，`run-33841231`）只证明管线能跑完；人工阅读未通过。见 [docs/STATUS.md](docs/STATUS.md)。
- README 里没有的命令，就还没有。PRD 里标了 **`[proposed]`** 的 CLI（`variant`、`canon confirm`、`chapter continue` 等）不要写成已经支持。

## 文档权威（只按这个顺序）

1. [docs/prd-v1-writing-assist.md](docs/prd-v1-writing-assist.md) — 产品。工作流 **W0–W6** 只在这里展开，本文件不复述。
2. [docs/adr/0001-plan-first-facts.md](docs/adr/0001-plan-first-facts.md) — 事实写入方向。
3. [docs/STATUS.md](docs/STATUS.md) — 工程事实（版本、闸门、已知限制）。
4. [docs/HANDOFF-mew.md](docs/HANDOFF-mew.md) — 当天的下一步。
5. [tasks/](tasks/README.md) — 有任务文档之后才算队列。清理被接受之前，队列是空的。

冲突时，上面的条目压过下面的。不要用归档路线图推翻 PRD。

## 默认不要读

这些文件历史还在，但会撑爆上下文，而且口径已过时：

- `docs/archive/` 全部。说明在 [docs/archive/README.md](docs/archive/README.md)。
- `docs/archive/architecture/04-vibe-coding-engineering.md` 里的 Task 001–019。那不是活队列。
- `docs/archive/architecture/05-tech-reference.md`。
- `docs/archive/roadmap/` 下的 V13 / V14 / V15。
- `docs/archive/ROADMAP-plan-first.md` 全文。短指针 [docs/ROADMAP-plan-first.md](docs/ROADMAP-plan-first.md) 写明 **CLOSED**。
- `docs/archive/experiments/**` 里的章节正文。那是 plan-gate 重跑留档，不是文学交付。

地图：[docs/INDEX.md](docs/INDEX.md)。安装与短窗口仍走 [docs/quickstart.md](docs/quickstart.md)。

## 不要沿这些方向加功能

- 不要把 extract-then-patch，或 SettlementExtractor 的自动写入，做成助手主路径。确认入典才是写入 Canon 的作者路径。
- 不要为了追召回去加题材专用检查器。窄检查保持薄封装。
- 不要把质量门通过写成「可发表」或「书写得好」。
- 不要提交 `.env`、密钥、书稿、本地数据库、未脱敏日志。

## 运行时不变量

- **SQLite 是唯一长期事实源。** 不要另起一套权威库。
- **章节版本只追加。** 草稿、修订、已接收版本都留着，不覆盖旧稿。
- **提示词**在 `src/songyan/prompts/cards/`。不要把长提示词嵌进 Python。
- 已批准的计划卡才进入当前章的事实圣经。`pending` 行不能被下一章当成已成立事实。

## 怎么干活

1. 读本文件和当前任务（`tasks/NNN-*.md`，或 HANDOFF 里的下一刀）。没有任务文档就不要口头开工。
2. 切片要小。一次只做下一刀里的一件事。
3. 行为变了就同步 [docs/STATUS.md](docs/STATUS.md) 和 [docs/HANDOFF-mew.md](docs/HANDOFF-mew.md)。进度不要写进 README。
4. 测试怎么放、哪些必须绿，见 [tests/README.md](tests/README.md)。新测试禁止 `test_task###_*.py`、`test_<数字>_*.py`、`test_v<数字>_*.py`。
5. 提交前跑 `ruff check src/ tests/`，以及与改动对应的 pytest。命令见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 命令表面（避免说错）

现网能用的是已经安装的 Click 命令，例如 `doctor`、`create-project`、`run`、`report`、`export`、`import`、`bundle-run`。分组别名和抽卡命令以 PRD 为准；标了 proposed 的都还没做。Git 式整树 `branch` 不在 V1.0。

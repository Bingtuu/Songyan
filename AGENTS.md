# AGENTS.md

给在本仓库里改代码或改文档的人或代理。先读本文件，再读当前任务。不要把 `docs/archive/` 收进默认上下文。

## 现在是什么

Songyan（松烟）是 **人主导的连载写作助手**，接在现有的事实 / 故事线工作台上。人决定事实、数据、人物、时间、道具、伏笔、故事线和终稿。系统记录、检索、发现冲突、审计变更、报告一致性。

两条日常路径：

1. **先稿后典：** 草稿 → 结算事实 / 数据 → 人改编 → 审读 / 检查。
2. **工作台先行：** 人编辑事实与故事线，系统提供一致性支持。

当前可运行的包是 **v0.5**（`pyproject.toml` 的 `0.5.0`）。「V1.0」是产品代际名，不是版本号。不要打 `v1.0` 标签，不要为了文档改版本号。

都市灵异是 Phase C 的试点和 M0 夹具（《末班铜牌》），不是以后唯一题材。不要为此加题材检查器。

## 现在不是什么

- 不是无人值守写完一本小说，也不是自动改写终稿。`songyan run --chapters 1-N --auto-confirm` 是引擎 / 冒烟 / 长窗实验。
- 不是纯设定台账。写作辅助留在产品里。
- 不会静默改 Canon。抽取、结算摘要、审读建议默认是提案。确认入典才是作者写入路径。
- 章内 Variant 不是 Git 分支。默认 N=2。Git 式整树 `branch` 不在这一代。
- 不拥有文学质量。Ch1–10（`47954cb`，`run-33841231`）只证明管线能跑完。见 [docs/STATUS.md](docs/STATUS.md)。
- README 里没有的命令，就还没有。PRD 里标了 **`[proposed]`** 的命令不要写成已经支持。

## 文档权威

1. [docs/prd-v1.md](docs/prd-v1.md) — 产品。工作流 W0–W6、路径 P-draft / P-bench、里程碑 M0–M4 只在这里展开。Owner 已接受。
2. [docs/tech-m0.md](docs/tech-m0.md) — 只规划 M0。步 1–4 已进 `main`；§6–7 代码验收 **PASS**（`80f4107`）。
3. [docs/tech-m1.md](docs/tech-m1.md) — 只规划 M1（人确认入典 + 规则 `check`）。**已接受（Mew 拍板，2026-11-03 Asia/Shanghai）。** 步 1–5 已进 `main`；§6–7 代码验收 **PASS**（`69d7ece`）。不得越出 PRD 的 M1。
4. [docs/tech-m2.md](docs/tech-m2.md) — 只规划 M2（硬事实标脏、承诺债务、抽取提案）。**已接受**（2026-11-04 Asia/Shanghai；owner widget t93s804；B1–B6 原样）。不得越出 PRD 的 M2。
5. [docs/adr/0001-plan-first-facts.md](docs/adr/0001-plan-first-facts.md) — 事实写入方向。
6. [docs/STATUS.md](docs/STATUS.md) — 工程事实（版本、闸门、已知限制）。
7. [docs/HANDOFF-mew.md](docs/HANDOFF-mew.md) — 当天的下一步。
8. [tasks/](tasks/README.md) — 队列从 `tasks/200-` 起。没有任务文件就不要口头开工。

冲突时，上面的条目压过下面的。产品边界以 PRD 为准；M0 的实现细节以 `tech-m0.md` 为准；M1 的实现细节以**已接受的** `tech-m1.md` 为准；M2 的实现细节以**已接受的** `tech-m2.md` 为准，且不得越出 PRD 对应里程碑。不要用归档路线图或 [docs/prd-v1-writing-assist.md](docs/prd-v1-writing-assist.md) 的指针页推翻 PRD。

**开工门（M2 已开）：** `docs/tech-m2.md` **已接受**（2026-11-04；t93s804；B1–B6 原样）。步 1–2 已合入；下一刀为 M2 步 3（`--hard` / `content_stale`），**仅 owner/parent 授权后**：先建 `tasks/21x`，再改 `src/` / `tests/`；TDD；开 PR 后 Mew COMMENT 再合并。M3 及以后各自另有被接受的技术方案。

## 默认不要读

- `docs/archive/` 全部。说明在 [docs/archive/README.md](docs/archive/README.md)。其中有 2026-10-26 的 AGENTS、STATUS、PRD 副本。
- `docs/archive/architecture/` 里的 Task 001–019。那不是活队列。
- `docs/archive/roadmap/` 下的 V13 / V14 / V15。
- `docs/archive/ROADMAP-plan-first.md` 全文。短指针写明 **CLOSED**。
- `docs/archive/experiments/**` 里的章节正文。

地图：[docs/INDEX.md](docs/INDEX.md)。安装与短窗口仍走 [docs/quickstart.md](docs/quickstart.md)。

## 不要沿这些方向加功能

- 不要把 extract-then-patch，或 SettlementExtractor 的自动写入，做成助手主路径。
- 不要为了追召回去加题材专用检查器。窄检查保持薄封装。
- 不要把质量门通过写成「可发表」或「书写得好」。
- tech-m2 **已接受**：只按已接受 tech-m2 的**已授权**当前步改 `src/` / `tests/`；不做未授权的步 3+。抽卡 / 续写仍属更后里程碑。M1 约束仍有效（五表 `rejected`；无持久第四态 `accepted`）。
- 不要提交 `.env`、密钥、书稿、本地数据库、未脱敏日志。

## 运行时不变量

- **SQLite 是唯一长期事实源。**
- **章节版本只追加。**
- **提示词**在 `src/songyan/prompts/cards/`。
- 已批准的计划卡才进入当前章的事实圣经。`pending` 行不能被下一章当成已成立事实。
- 故事线（大纲 / 弧 / 线索）不是 Canon 的别名。

## 怎么干活

1. 读本文件。要改产品行为时，先确认 owner 已经书面接受第「文档权威」节里的开工门。
2. 切片要小。一次只做下一刀里的一件事。M0 的步序在技术方案里。
3. 行为变了就同步 [docs/STATUS.md](docs/STATUS.md) 和 [docs/HANDOFF-mew.md](docs/HANDOFF-mew.md)。进度不要写进 README。
4. 测试怎么放、哪些必须绿，见 [tests/README.md](tests/README.md)。新测试禁止 `test_task###_*.py`、`test_<数字>_*.py`、`test_v<数字>_*.py`。
5. 提交前跑 `ruff check src/ tests/`，以及与改动对应的 pytest。命令见 [CONTRIBUTING.md](CONTRIBUTING.md)。`tests/cli` 不在默认收集里，改了 CLI 就要单独跑。

## 简报

给 owner 审这代产品的简报只用简体中文，写在 PR 说明、`docs/STATUS.md`、`docs/HANDOFF-mew.md`。命令、路径、表名、测试名保持仓库里的英文标识。不要另造评审流程、频道或第二套任务队列。

## 命令表面

现网能用的包括 `doctor`、`create-project`、`run`、`report`、`export`、`import`、`bundle-run`，以及 M0 的 `canon show` 与 `today`，以及 M1 的 `canon edit` / `confirm` / `dismiss`（及非持久 `accept`；entity/attribute）与规则 `check`，以及 M2 步 1 的 `today` 承诺计数与 `canon show --kind promise`（只读，不是 Canon），以及 M2 步 2 的 `canon confirm promise` 人销账。`variant`、`chapter continue`、`review` 与 M2 步 3+（`--hard` / `content_stale` / extract）仍是更后小步。完整列表以 PRD 第 9 节为准。

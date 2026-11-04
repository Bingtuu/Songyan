# Songyan 状态

给冷启动的人：现在能跑的是什么，V1.0 文档走到哪，什么还没做。

包版本 **0.5.0**（owner 称之为 v0.5）。**V1.0** 是写作助手这一代的产品名，不是这个包版本。本页不打 git tag，也不改 `pyproject.toml`。

Package tip remains **0.5.0**. V1.0 is the product-generation name.

## 这一轮

| 项 | 状态 |
|----|------|
| 产品需求 [prd-v1.md](prd-v1.md) 与 [tech-m0.md](tech-m0.md) | Owner 已接受文档切分。[#27](https://github.com/Bingtuu/Songyan/pull/27) 已 squash 进 `main` |
| M0 步 1 `canon show` | **已在 `main`。** [#28](https://github.com/Bingtuu/Songyan/pull/28) squash 为 `1d8c0c0`。任务归档在 [tasks/done/200.md](../tasks/done/200.md) |
| M0 步 2 故事线 | **已在 `main`。** [#29](https://github.com/Bingtuu/Songyan/pull/29) squash 为 `8f03453`。任务归档在 [tasks/done/201.md](../tasks/done/201.md) |
| M0 步 3 `today` | **已在 `main`。** [#30](https://github.com/Bingtuu/Songyan/pull/30) squash 为 `d5c2cc1`。任务归档在 [tasks/done/202.md](../tasks/done/202.md) |
| M0 步 4 缺库 / 缺项目退出码 | **已在 `main`。** [#31](https://github.com/Bingtuu/Songyan/pull/31) squash 为 `48fa354`。任务归档在 [tasks/done/203.md](../tasks/done/203.md) |
| M0 代码验收（步 1–4 + tech-m0 §6–7） | **PASS**（`main` `80f4107`）。证据见 [tasks/done/204-m0-acceptance.md](../tasks/done/204-m0-acceptance.md)。S6（一周打开 3 天）不在代码验收内 |
| M1 技术方案 [tech-m1.md](tech-m1.md) | **已接受（Mew 拍板，2026-11-03 Asia/Shanghai，owner t82u 授权）。** 绑定决策已写入正文 |
| M1 步 1 `rejected` 迁移 + 过滤 | **已在 `main`。** [#35](https://github.com/Bingtuu/Songyan/pull/35) squash 为 `1995181`。任务归档在 [tasks/done/205-rejected迁移与过滤.md](../tasks/done/205-rejected迁移与过滤.md) |
| M1 步 2 `canon edit` | **已在 `main`。** [#36](https://github.com/Bingtuu/Songyan/pull/36) squash 为 `5a260a9`。任务归档在 [tasks/done/206-canon-edit.md](../tasks/done/206-canon-edit.md) |
| M1 步 3 `confirm` + `dismiss` | **已在 `main`。** [#38](https://github.com/Bingtuu/Songyan/pull/38) squash 为 `7c7ec43`。任务归档在 [tasks/done/207-confirm-dismiss.md](../tasks/done/207-confirm-dismiss.md) |
| M1 步 4 `check`（W6） | **已在 `main`。** [#39](https://github.com/Bingtuu/Songyan/pull/39) squash 为 `d3f127c`。任务归档在 [tasks/done/208-check.md](../tasks/done/208-check.md) |
| M1 步 5 W0 e2e + `today` next | **已在 `main`。** [#41](https://github.com/Bingtuu/Songyan/pull/41) squash 为 `69d7ece`。任务归档在 [tasks/done/209-w0-today-e2e.md](../tasks/done/209-w0-today-e2e.md) |
| M1 代码验收（步 1–5 + tech-m1 §6–7） | **PASS**（`main` `69d7ece`）。证据见 [tasks/done/210-m1-acceptance.md](../tasks/done/210-m1-acceptance.md)。S1/S2 产品周期日志不在代码验收内 |
| M2 技术方案 [tech-m2.md](tech-m2.md) | **已接受**（2026-11-04 Asia/Shanghai；owner widget t93s804；B1–B6 原样接受；[#43](https://github.com/Bingtuu/Songyan/pull/43) squash `a95824a`） |
| M2 步 1 W5 只读 | **PR 待 COMMENT**（分支 `m2-step1-w5-readonly`；任务 [tasks/212-m2-step1-w5-readonly.md](../tasks/212-m2-step1-w5-readonly.md)） |
| 包版本 | 仍是 `0.5.0` |

tech-m2 **已接受**。M2 步 1（W5 只读）进行中。不要声称 V1.0 完成，不要升包版本（仍 `0.5.0`）。不做步 2+。

上一稿 PRD 的总体框架 owner 已经接受。现行文本是 `prd-v1.md`。旧全文在 [archive/prd-v1-writing-assist-2026-10-26.md](archive/prd-v1-writing-assist-2026-10-26.md)。

## 发布就绪（v0.5 引擎）

这些是既有工程事实，不是 V1.0 里程碑。

| 项 | 状态 |
|----|:----:|
| 源码安装、wheel、非仓库目录的 CLI、包资源 | PASS |
| SQLite 初始化、模板建项、已接收书稿导出冒烟 | PASS |
| CLI 测试 / 默认 pytest / ruff / 运行时 mypy | PASS |
| 真实模型冒烟 | Ch1–3 在 `eaa6bef`（#20）**PASS**。Ch1–10 在 `47954cb`：**管线 PASS，DG-1 失败，文学失败** |

**v0.5** 是能用的技术预览。闸门在 `47954cb` 上验证到第 10 章；文学没有过。正式 tag 仍由维护者决定。

## 现在能用

- 本机 Python CLI、SQLite、模板、`doctor`。
- `create-project`、`run`、`report`、`metrics`、`five-gate`、`t9`、`bundle-run`、`export`、`backup`、`restore`。
- `profile` 的 `validate` / `upsert --dry-run` / `history` / `rollback`。按角色的 `LLM_<ROLE>_*` 路由。
- `import`（`ingest`、`segment`、`confirm`、`status`、`replay`、`synthesize`、`publish`）。`publish` 之前 `run` 保持阻塞。
- 计划事实表与 `load_chapter_plan_bible`：只读 `approved`。结算写入仍进结算库，不进 plan canon。
- `canon show` 在 `main` 上能看五类计划事实的 Canon / Pending，以及故事线骨架（有则打印，无则为 `（空）`），并支持 `--json`。
- `today` 在 `main` 上能打印只读计数与固定 `next`（`可用 canon confirm 入典；生成不在本命令。`）。
- 缺库 / 缺项目时 `canon show` 与 `today` 退出码 1；缺库时不创建数据库文件。
- `canon edit` 在 `main` 上能写入 entity / attribute 为 `pending`；attribute 强制 `source=human`；Pending 可见，Canon / 圣经不可见。
- `canon confirm` / `dismiss` / 非持久 `accept`：在 `main` 上（entity+attribute）。
- `check` 在 `main` 上：只读规则报告；正文取自 accepted `ChapterVersion.content`；属性侧值可经 `--extracts-json` 注入。

## 已知限制

- 只有 CLI，不是托管服务。真实生成要 API key，并且花钱。
- 《轨道蜃景》Ch1–10：`project_id=8e30dec7f2ec40c1a9ce54c783981f8c`，`run-33841231`。10/10 accepted；质量门、结算、摘要、导出通过；exit 0。**DG-1 失败**（平均 revision 1.7，十章都有 ContextEmergency，无 AutoHalt）。
- 那次导出的人工阅读 **未通过**：时间线回滚、Hermes/赫耳墨斯、时间尺度、供氧 / EVA 复读、英文泄漏 `ninety-two 秒`。
- 真实模型上「导入后再续写」还没有验收。
- `variant`、`chapter continue` 都还没有。tech-m1 **已接受**；步 1–5 与 §6–7 代码验收已 **PASS**（`69d7ece`）。[tech-m2.md](tech-m2.md) **已接受**；下一刀 = M2 步 1 编码。M3/M4 各自另有被接受的技术方案。

标识和本机路径：[HANDOFF-mew.md](HANDOFF-mew.md)。书稿不入库。

## 文档

| 文件 | 用途 |
|------|------|
| [README](../README.md) | 给访客的概览 |
| [AGENTS.md](../AGENTS.md) | 冷启动规则：读什么、何时不许写代码 |
| [V1.0 PRD](prd-v1.md) | 产品。Owner 已接受这轮文档 |
| [M0 技术方案](tech-m0.md) | 只读工作台。步 1–4 已进 `main`；§6–7 代码验收 **PASS**（`80f4107`） |
| [M1 技术方案](tech-m1.md) | 人确认入典 + 规则 `check`。**已接受（Mew 拍板）**；步 1–5 已合入；§6–7 代码验收 **PASS**（`69d7ece`） |
| [M2 技术方案](tech-m2.md) | 硬事实标脏 + 承诺债务 + 抽取提案。**已接受**（2026-11-04；B1–B6 原样） |
| [ADR-0001](adr/0001-plan-first-facts.md) | 事实由计划和人写入 |
| [HANDOFF](HANDOFF-mew.md) | 当天的下一步 |
| [INDEX](INDEX.md) | 文档地图 |
| [Quickstart](quickstart.md) | 安装和短窗口 |
| [质量门](quality-gates.md) | CED / T9 / 五门。通过不等于写得好 |

## 维护者下一步

1. **M1 已代码验收 PASS。** [tech-m2.md](tech-m2.md) 草稿已出；下一闸门：owner **书面接受** tech-m2；接受前不开 M2 编码。
2. 不要合成大 PR，不要在接受前开 M2 / variant / continue 编码，不要在接受前改结算权威。
3. 不加题材检查器、不跑无人值守长篇、不升包版本、不声称 V1.0 完成。

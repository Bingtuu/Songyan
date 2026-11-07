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
| M2 步 1 W5 只读 | **已在 `main`。** [#44](https://github.com/Bingtuu/Songyan/pull/44) squash 为 `8f7bc77`。任务归档在 [tasks/done/212-m2-step1-w5-readonly.md](../tasks/done/212-m2-step1-w5-readonly.md) |
| M2 步 2 W5 人确认销账 | **已在 `main`。** [#46](https://github.com/Bingtuu/Songyan/pull/46) squash 为 `8afb7be`。任务归档在 [tasks/done/213-m2-step2-confirm-settle.md](../tasks/done/213-m2-step2-confirm-settle.md) |
| M2 步 3 W4 content_stale + `--hard` | **已在 `main`。** [#48](https://github.com/Bingtuu/Songyan/pull/48) squash 为 `2ac1093`。任务归档在 [tasks/done/214-m2-step3-content-stale-hard.md](../tasks/done/214-m2-step3-content-stale-hard.md) |
| M2 步 4 check 报告 stale 范围 | **已在 `main`。** [#50](https://github.com/Bingtuu/Songyan/pull/50) squash 为 `5a6e923`。任务归档在 [tasks/done/215-m2-step4-check-stale-report.md](../tasks/done/215-m2-step4-check-stale-report.md) |
| M2 步 5 extract→pending | **已在 `main`。** [#52](https://github.com/Bingtuu/Songyan/pull/52) squash 为 `2fa8209`。任务归档在 [tasks/done/216-m2-step5-extract-pending.md](../tasks/done/216-m2-step5-extract-pending.md) |
| M2 步 6 闭环文案与文档同步 | **已在 `main`。** [#53](https://github.com/Bingtuu/Songyan/pull/53) squash 为 `f1c3093`。任务归档在 [tasks/done/217-m2-step6-docs-copy.md](../tasks/done/217-m2-step6-docs-copy.md) |
| M2 代码验收（步 1–6 + tech-m2 §6–7） | **PASS**（证据 tip `main` `f1c3093`）。证据见 [tasks/done/218-m2-acceptance.md](../tasks/done/218-m2-acceptance.md)。S3 产品周期数值不在代码验收内 |
| M3 技术方案 [tech-m3.md](tech-m3.md) | **已接受**（2026-11-06 Asia/Shanghai；owner widget t104s937；B1–B7 原样） |
| M3 步 1 表 + fingerprint + 仓库 + `variant list` | **已在 `main`。** [#56](https://github.com/Bingtuu/Songyan/pull/56) squash 为 `b9bbf98`。任务归档在 [tasks/done/220-m3-step1-variants-table.md](../tasks/done/220-m3-step1-variants-table.md) |
| M3 步 2 `variant generate` | **已在 `main`。** [#57](https://github.com/Bingtuu/Songyan/pull/57) squash 为 `135fcfb`。任务归档在 [tasks/done/221-m3-step2-variant-generate.md](../tasks/done/221-m3-step2-variant-generate.md) |
| M3 步 3 `variant list` / `diff` | **进行中**（本 PR）。任务 [tasks/done/222-m3-step3-variant-list-diff.md](../tasks/done/222-m3-step3-variant-list-diff.md)（开 PR 后归档） |
| 包版本 | 仍是 `0.5.0` |

tech-m2 **已接受**。M2 步 1–6 **已在 `main`**（#44 / `8f7bc77`；#46 / `8afb7be`；#48 / `2ac1093`；#50 / `5a6e923`；#52 / `2fa8209`；#53 / `f1c3093`）。§6–7 代码验收 **PASS**（证据 tip `f1c3093`；见 [tasks/done/218-m2-acceptance.md](../tasks/done/218-m2-acceptance.md)）。[tech-m3.md](tech-m3.md) **已接受**（2026-11-06；t104s937；B1–B7 原样）。M3 步 1 **已在 `main`**（#56 / `b9bbf98`）。M3 步 2 **已在 `main`**（#57 / `135fcfb`）。**M3 步 3 编码进行中**（本 PR；owner t104s965）。不要声称 V1.0 完成，不要升包版本（仍 `0.5.0`）。不要开 continue / review / 步 4+（仅步 3 合入且再授权后）。

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
- 计划事实表与 `load_chapter_plan_bible`：只读 `approved`（属性 source 含 plan|human|extract）。结算写入仍进结算库（`untrusted_until_confirmed`），并另入队 `plan_*` pending（source=extract）；confirm 前不进 canon。
- `canon show` 在 `main` 上能看五类计划事实的 Canon / Pending，以及故事线骨架（有则打印，无则为 `（空）`），并支持 `--json`。
- `today` 在 `main` 上能打印只读计数与固定 `next`（`可用 canon confirm 入典或销账承诺；硬确认可用 --hard/--mark-stale；生成不在本命令。`）。
- 缺库 / 缺项目时 `canon show` 与 `today` 退出码 1；缺库时不创建数据库文件。
- `canon edit` 在 `main` 上能写入 entity / attribute 为 `pending`；attribute 强制 `source=human`；Pending 可见，Canon / 圣经不可见。
- `canon confirm` / `dismiss` / 非持久 `accept`：在 `main` 上（entity+attribute）；`canon confirm promise`（章号+证据）人销账亦在 `main`（#46 / `8afb7be`）。`canon confirm` `--hard` / `--mark-stale` 与 `chapter_heads.content_stale` 亦在 `main`（#48 / `2ac1093`）。
- `check` 在 `main` 上：只读规则报告；正文取自 accepted `ChapterVersion.content`；属性侧值可经 `--extracts-json` 注入；亦报告 `content_stale` / 受影响章范围（#50 / `5a6e923`）。
- `today` 在 `main` 上含 `promise_planted` / `promise_due` / `promise_overdue` 只读计数（text + json）。
- `canon show --kind promise` 在 `main` 上列出开放承诺；默认 `canon show` 不把承诺标成 Canon。

## 已知限制

- 只有 CLI，不是托管服务。真实生成要 API key，并且花钱。
- 《轨道蜃景》Ch1–10：`project_id=8e30dec7f2ec40c1a9ce54c783981f8c`，`run-33841231`。10/10 accepted；质量门、结算、摘要、导出通过；exit 0。**DG-1 失败**（平均 revision 1.7，十章都有 ContextEmergency，无 AutoHalt）。
- 那次导出的人工阅读 **未通过**：时间线回滚、Hermes/赫耳墨斯、时间尺度、供氧 / EVA 复读、英文泄漏 `ninety-two 秒`。
- 真实模型上「导入后再续写」还没有验收。
- `variant list` / `generate` 已在 `main`（#56 / #57）；`variant list` 字段增强与 `diff` 随 M3 步 3 落地（本 PR）；`pick` / `abandon` 与 `chapter continue` 都还没有。tech-m1 **已接受**；步 1–5 与 §6–7 代码验收已 **PASS**（`69d7ece`）。[tech-m2.md](tech-m2.md) **已接受**；步 1–6 已在 `main`；§6–7 代码验收 **PASS**（证据 tip `f1c3093`）。[tech-m3.md](tech-m3.md) **已接受**（t104s937；B1–B7）；**步 3 进行中**。M4 另有被接受的技术方案并授权之后才开工。

标识和本机路径：[HANDOFF-mew.md](HANDOFF-mew.md)。书稿不入库。

## 文档

| 文件 | 用途 |
|------|------|
| [README](../README.md) | 给访客的概览 |
| [AGENTS.md](../AGENTS.md) | 冷启动规则：读什么、何时不许写代码 |
| [V1.0 PRD](prd-v1.md) | 产品。Owner 已接受这轮文档 |
| [M0 技术方案](tech-m0.md) | 只读工作台。步 1–4 已进 `main`；§6–7 代码验收 **PASS**（`80f4107`） |
| [M1 技术方案](tech-m1.md) | 人确认入典 + 规则 `check`。**已接受（Mew 拍板）**；步 1–5 已合入；§6–7 代码验收 **PASS**（`69d7ece`） |
| [M2 技术方案](tech-m2.md) | 硬事实标脏 + 承诺债务 + 抽取提案。**已接受**（2026-11-04；B1–B6 原样）；步 1–6 已合入；§6–7 代码验收 **PASS**（证据 tip `f1c3093`） |
| [M3 技术方案](tech-m3.md) | 章内 Variant / 抽卡。**已接受**（2026-11-06；t104s937；B1–B7 原样）；步 1–2 已合入；步 3 编码进行中 |
| [ADR-0001](adr/0001-plan-first-facts.md) | 事实由计划和人写入 |
| [HANDOFF](HANDOFF-mew.md) | 当天的下一步 |
| [INDEX](INDEX.md) | 文档地图 |
| [Quickstart](quickstart.md) | 安装和短窗口 |
| [质量门](quality-gates.md) | CED / T9 / 五门。通过不等于写得好 |

## 维护者下一步

1. **tech-m3 已接受**（t104s937；B1–B7 原样）。步 1–2 已在 `main`（#56 / `b9bbf98`；#57 / `135fcfb`）。**当前 = M3 步 3**（`variant list`/`diff`；owner t104s965）。步 3 合入后，下一闸门 = owner/parent 授权再开步 4（`pick`/`abandon`）。
2. 不要改结算权威；不要合成大 PR；不做步 4+ / continue / review。
3. 不加题材检查器、不跑无人值守长篇、不升包版本、不声称 V1.0 完成。

# Songyan 状态

给冷启动的人：现在能跑的是什么，V1.0 文档走到哪，什么还没做。

包版本 **0.5.0**（owner 称之为 v0.5）。**V1.0** 是写作助手这一代的产品名，不是这个包版本。本页不打 git tag，也不改 `pyproject.toml`。

Package tip remains **0.5.0**. V1.0 is the product-generation name.

## 这一轮

| 项 | 状态 |
|----|------|
| 产品需求 [prd-v1.md](prd-v1.md) | 已写入，**待 owner 书面接受** |
| M0 技术方案 [tech-m0.md](tech-m0.md) | 已写入，**待 owner 书面接受**。只覆盖只读工作台 |
| `AGENTS.md` / 本页 | 已按重启后的冷启动规则替换。旧文在 `docs/archive/`，日期 2026-10-26 |
| M0 代码 | **没有开始。** 不要把文档合并当成 `canon show` 已可用 |
| `tasks/200` | **没有。** 四份文档被接受之前不写 |

阻塞：owner（Bingtuu）书面接受 PRD、M0 技术方案、`AGENTS.md` 和本页之前，不开 M0 实现。只接受其中一份不够。M1 及以后另写技术方案，不在 M0 里预做。

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
- 故事线骨架表（大纲 / 弧 / 线索）已有读写库，**没有**作者向只读 CLI。那是 M0 要补的，现在还没有。

## 已知限制

- 只有 CLI，不是托管服务。真实生成要 API key，并且花钱。
- 《轨道蜃景》Ch1–10：`project_id=8e30dec7f2ec40c1a9ce54c783981f8c`，`run-33841231`。10/10 accepted；质量门、结算、摘要、导出通过；exit 0。**DG-1 失败**（平均 revision 1.7，十章都有 ContextEmergency，无 AutoHalt）。
- 那次导出的人工阅读 **未通过**：时间线回滚、Hermes/赫耳墨斯、时间尺度、供氧 / EVA 复读、英文泄漏 `ninety-two 秒`。
- 真实模型上「导入后再续写」还没有验收。
- 作者向 `canon` / `today` / `check` / `variant` / `chapter continue` 都还没有安装。

标识和本机路径：[HANDOFF-mew.md](HANDOFF-mew.md)。书稿不入库。

## 文档

| 文件 | 用途 |
|------|------|
| [README](../README.md) | 给访客的概览 |
| [AGENTS.md](../AGENTS.md) | 冷启动规则：读什么、何时不许写代码 |
| [V1.0 PRD](prd-v1.md) | 产品。待书面接受 |
| [M0 技术方案](tech-m0.md) | 只读工作台。待书面接受 |
| [ADR-0001](adr/0001-plan-first-facts.md) | 事实由计划和人写入 |
| [HANDOFF](HANDOFF-mew.md) | 当天的下一步 |
| [INDEX](INDEX.md) | 文档地图 |
| [Quickstart](quickstart.md) | 安装和短窗口 |
| [质量门](quality-gates.md) | CED / T9 / 五门。通过不等于写得好 |

## 维护者下一步

1. 审本轮文档 PR：PRD、M0 技术方案、AGENTS、本页。书面接受或指出要改的边界。
2. 接受之后只开 M0，按 `tech-m0.md` 的步序写 `tasks/200` 起的任务。一次一步。
3. 不在 M0 里改结算权威、不加题材检查器、不跑无人值守长篇、不升包版本。

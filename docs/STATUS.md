# Songyan 状态

给冷启动 / **owner 短暂接手开发** 的人：现在 tip 在哪、能跑什么、下一闸门是什么、什么还没做。

包版本 **0.5.0**（owner 称之为 v0.5）。**V1.0** 是写作助手这一代的产品名，不是这个包版本。本页不打 git tag，也不改 `pyproject.toml`。

## 接手节点（2026-11-07 Asia/Shanghai）

| 项 | 值 |
|----|----|
| **git tip（`main`）** | `f72590b` — docs handoff [#61](https://github.com/Bingtuu/Songyan/pull/61)（STATUS/README 对齐） |
| **功能 tip（M3 步 1–5）** | `1b0e323` — [#60](https://github.com/Bingtuu/Songyan/pull/60)（`stale_vs_canon` + list 费用） |
| **包版本** | 仍是 `0.5.0`（不 bump） |
| **里程碑** | M0 / M1 / M2 代码验收 **PASS**；M3 技术方案已接受；**M3 步 1–5 已在 `main`** |
| **下一闸门** | **M3 步 6**（闭环文案与文档同步，见 [tech-m3.md](tech-m3.md) §5）— **仅 owner 授权后才开**；当前 owner 选择「先等等」 |
| **本 handoff** | 文档对齐便于接手；**不是**步 6 编码 |

硬约束（接手期间同样适用）：

- 不声称 V1.0 完成；不升包版本；不合成大 PR。
- 不改结算权威；结算库仍是 `untrusted_until_confirmed` 对照，不升格 Canon。
- 不开 `chapter continue` / `review`（M3 范围外）。
- 不加题材检查器；不跑无人值守长篇。
- 编码刀仍建议 TDD + 审阅后再合；小步 PR。

## 一眼进度

| 里程碑 | 状态 | tip / 证据 |
|--------|------|-----------|
| M0 只读工作台 | **PASS** | `80f4107` · [204](../tasks/done/204-m0-acceptance.md) |
| M1 人确认 + `check` | **PASS** | `69d7ece` · [210](../tasks/done/210-m1-acceptance.md) |
| M2 标脏 / 承诺 / extract→pending | **PASS** | `f1c3093` · [218](../tasks/done/218-m2-acceptance.md) |
| M3 技术方案 [tech-m3.md](tech-m3.md) | **已接受**（t104s937；B1–B7 原样） | #55 → `5101555` |
| M3 步 1–5 抽卡表面 | **已在 `main`** | 功能 tip `1b0e323`（#56–#60） |
| M3 步 6 闭环文案 | **未开**（等 owner） | tech-m3 §5 |
| M3 §6–7 代码验收 | **未声称** | — |
| M4+ | **未开** | 另需被接受的技术方案 |

## 现在能用（作者主路径）

工作台 / Canon / 检查（均已在 `main`）：

- `canon show` / `today`（只读；缺库缺项目 exit 1）
- `canon edit` → Pending；`confirm` / `dismiss` / 非持久 `accept`
- `canon confirm promise`；`confirm --hard` / `--mark-stale`（`content_stale`）
- `check`（只读规则报告；可报 `content_stale` 范围）

M3 章内抽卡（#56–#60 / 功能 tip `1b0e323`）：

```text
songyan variant generate --project-id TEXT --chapter INT [--n 2] [--budget-cny FLOAT] [--json]
songyan variant list     --project-id TEXT --chapter INT [--json]
songyan variant diff     --project-id TEXT --chapter INT --a INT --b INT [--json]
songyan variant pick     --project-id TEXT --chapter INT --slot INT [--allow-stale] [--json]
songyan variant abandon  --project-id TEXT --chapter INT --slot INT [--json]
```

语义要点（实现已落地，详见 tech-m3）：

- 默认 N=2；**不** auto-pick；`pick` **只**改 `ChapterHead.current_version_id`，**不**写 `plan_*` / Canon。
- `abandon` 软删；不物理清已 pick 正文。
- list / diff / pick / generate 前懒刷新 `stale_vs_canon`；stale pick 默认 exit 2，需 `--allow-stale`。
- `variant list` 暴露 per-slot `cost_cny_estimate`。
- `content_stale`（正文相对硬典）与 `stale_vs_canon`（草稿相对生成时 Canon 指纹）**并存**，文案勿混成一列。

既有管线仍可用：`create-project` / `run` / `report` / `import` / `doctor` / `backup` 等（`run --auto-confirm` 是冒烟路径，**不是**作者主路径）。

## 接手开发时先看这些

| 目的 | 文件 |
|------|------|
| 产品边界 | [prd-v1.md](prd-v1.md) |
| M3 做什么 / 不做什么 / 小步定义 | [tech-m3.md](tech-m3.md)（尤其 §3、§4、§5） |
| 当天下一步（给助手） | [HANDOFF-mew.md](HANDOFF-mew.md) |
| 冷启动规则 | [AGENTS.md](../AGENTS.md) |
| CLI 入口 | `src/songyan/cli/commands/variant.py`、`canon_write.py`、`workbench.py`、`check.py` |
| M3 服务 | `src/songyan/services/variant_{fingerprint,generate,diff,pick,stale}.py` |
| M3 仓库 | `src/songyan/db/chapter_variant_repo.py` |
| 步 5 归档 | [tasks/done/224-m3-step5-stale-cost.md](../tasks/done/224-m3-step5-stale-cost.md) |
| 本地回归（抽卡相关） | `tests/cli/test_variant_*.py`、`tests/services/test_variant_fingerprint.py`、`tests/db/test_chapter_variants.py` |

本地仓库路径（Diupi-Yun）：`C:\Vibe Project\Songyan`，应对齐 `origin/main` @ `f72590b`。

## 已知限制

- 只有 CLI，不是托管服务。真实生成要 API key，并且花钱。
- 《轨道蜃景》Ch1–10 管线曾 PASS、文学未过（DG-1 失败等）；细节见历史冒烟记录，不作 V1.0 文学验收。
- 真实模型上「导入后再续写」还没有验收。
- **未做：** M3 步 6；`chapter continue` / `review`；M3 §6–7 验收声称；M4+。
- `today` 的固定 `next` 文案仍是 M2 口径；若要改成「可抽卡」提示，属于**步 6**，需 owner 授权后再改。
- **2026-11-07 评审修复（task 226，已归档 `tasks/done/`）**：全量 code review 的 1 blocker + 4 major + minor 批已修复——settlement 声称的伏笔 resolve 只进提案（不再直写 `resolved`；唯一写径 = `canon confirm promise`）；`variant generate` 成本记账去重且归因 project/agent；pick 拒绝 abandoned 槽；LLM 失败保留已写槽并报 stderr；rejected 行不可被 confirm 直接转正；extract 提案跳过 rejected。详见 `tasks/done/226-review-findings-fix.md` 与 `docs/superpowers/plans/2026-11-07-m0-m3-review-audit.md`。
- **2026-11-07 审计补强（task 228，已归档 `tasks/done/`）**：`canon confirm promise` 的人证 evidence 落库（`foreshadowings.resolved_evidence`，写-only 审计列）；销账守卫与写入合并为原子 UPDATE（并发双销账恰一成交）。读口径与 open 集不变。
- **2026-11-08 P0-3 收口（task 232，已归档 `tasks/done/232-plan-default-pending.md`）**：plan 五模型 `approval_status` 默认值 `"approved"` → `"pending"`（owner 拍板方案 A）。不显式传状态构造的卡从此落入 pending 队列，不再静默直写 Canon；生产写入方与种子夹具本就显式传值，零行为变化。测试侧 26 处夹具语义卡显式补 `approved`，新增模型级默认行为锁。
- **环境项（留维护者调查）**：`test_llm_http_timeout`（litellm/httpx 在 Windows 下不对悬挂 socket 应用 request_timeout）；`test_191_ch200_harness.py`（子进程 `text=True` 按 cp936 解码 UTF-8 输出；`PYTHONUTF8=1` 下通过，与本机 locale 相关）。本机全量回归建议带 `PYTHONUTF8=1`。

标识与助手交接：[HANDOFF-mew.md](HANDOFF-mew.md)。书稿不入库。

## 文档

| 文件 | 用途 |
|------|------|
| [README](../README.md) | 访客概览 |
| [AGENTS.md](../AGENTS.md) | 冷启动：读什么、何时不许写代码 |
| [prd-v1.md](prd-v1.md) | V1.0 产品需求（已接受） |
| [tech-m0.md](tech-m0.md) / [tech-m1.md](tech-m1.md) / [tech-m2.md](tech-m2.md) | 已验收里程碑方案 |
| [tech-m3.md](tech-m3.md) | 抽卡；已接受；步 1–5 已合；步 6 待授权 |
| [ADR-0001](adr/0001-plan-first-facts.md) | 事实由计划和人写入 |
| [INDEX](INDEX.md) | 文档地图 |
| [quickstart.md](quickstart.md) | 安装短窗口 |

## 维护者下一步

1. **当前 tip `f72590b`（功能面 `1b0e323`）。** 步 6 等 owner 点头；未授权前不要开步 6+ / continue / review。
2. 不改结算权威；不大 PR；不 bump；不声称 V1.0 完成。
3. owner 本地接手期间：以本页 + tech-m3 为准；助手侧默认待命，不抢开步 6。

## 附录：里程碑流水（合入记录）

<details>
<summary>M0–M3 各步 PR / tip（展开）</summary>

| 项 | 状态 |
|----|------|
| 文档切分 PRD + tech-m0 | [#27](https://github.com/Bingtuu/Songyan/pull/27) → main |
| M0 步 1 `canon show` | [#28](https://github.com/Bingtuu/Songyan/pull/28) → `1d8c0c0` · [200](../tasks/done/200.md) |
| M0 步 2 故事线 | [#29](https://github.com/Bingtuu/Songyan/pull/29) → `8f03453` · [201](../tasks/done/201.md) |
| M0 步 3 `today` | [#30](https://github.com/Bingtuu/Songyan/pull/30) → `d5c2cc1` · [202](../tasks/done/202.md) |
| M0 步 4 退出码 | [#31](https://github.com/Bingtuu/Songyan/pull/31) → `48fa354` · [203](../tasks/done/203.md) |
| M0 验收 | **PASS** @ `80f4107` · [204](../tasks/done/204-m0-acceptance.md) |
| M1 方案 | [tech-m1.md](tech-m1.md) 已接受 |
| M1 步 1–5 | #35→`1995181`；#36→`5a260a9`；#38→`7c7ec43`；#39→`d3f127c`；#41→`69d7ece` |
| M1 验收 | **PASS** @ `69d7ece` · [210](../tasks/done/210-m1-acceptance.md) |
| M2 方案 | [tech-m2.md](tech-m2.md) 已接受（#43→`a95824a`） |
| M2 步 1–6 | #44→`8f7bc77`；#46→`8afb7be`；#48→`2ac1093`；#50→`5a6e923`；#52→`2fa8209`；#53→`f1c3093` |
| M2 验收 | **PASS** @ `f1c3093` · [218](../tasks/done/218-m2-acceptance.md) |
| M3 方案 | [tech-m3.md](tech-m3.md) 已接受（#55→`5101555`） |
| M3 步 1 | [#56](https://github.com/Bingtuu/Songyan/pull/56) → `b9bbf98` · [220](../tasks/done/220-m3-step1-variants-table.md) |
| M3 步 2 | [#57](https://github.com/Bingtuu/Songyan/pull/57) → `135fcfb` · [221](../tasks/done/221-m3-step2-variant-generate.md) |
| M3 步 3 | [#58](https://github.com/Bingtuu/Songyan/pull/58) → `0b47410` · [222](../tasks/done/222-m3-step3-variant-list-diff.md) |
| M3 步 4 | [#59](https://github.com/Bingtuu/Songyan/pull/59) → `c38ee31` · [223](../tasks/done/223-m3-step4-variant-pick-abandon.md) |
| M3 步 5 | [#60](https://github.com/Bingtuu/Songyan/pull/60) → `1b0e323` · [224](../tasks/done/224-m3-step5-stale-cost.md) |
| docs handoff | [#61](https://github.com/Bingtuu/Songyan/pull/61) → `f72590b` · [225](../tasks/done/225-docs-handoff-status-readme.md) |

</details>

## 发布就绪（v0.5 引擎，历史）

| 项 | 状态 |
|----|:----:|
| 源码安装、wheel、非仓库目录 CLI、包资源 | PASS |
| SQLite 初始化、模板建项、已接收书稿导出冒烟 | PASS |
| CLI 测试 / 默认 pytest / ruff / 运行时 mypy | PASS |
| 真实模型冒烟 | Ch1–3 @ `eaa6bef` **PASS**；Ch1–10 @ `47954cb` 管线 PASS、DG-1/文学失败 |

**v0.5** 是能用的技术预览。正式 tag 仍由维护者决定。

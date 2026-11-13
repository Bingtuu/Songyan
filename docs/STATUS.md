# Songyan 状态

给冷启动 / **owner 短暂接手开发** 的人：现在 tip 在哪、能跑什么、下一闸门是什么、什么还没做。

包版本 **0.5.0**（owner 称之为 v0.5）。**V1.0** 是写作助手这一代的产品名，不是这个包版本。本页不打 git tag，也不改 `pyproject.toml`。

## 接手节点（2026-11-13 Asia/Shanghai）

| 项 | 值 |
|----|----|
| **git tip（`main`）** | `131116d`（M3/F1 评估闭环：remove 不存在 id 钉死 exit 2 + arc_index 自动分配）；本地领先 origin 17 提交未 push；此前 @ `ede0931`（已 push） |
| **功能面** | M0–M4（@ `e5a33bd`）+ post-M4：`chapter status`(248) / `review --deep`(250) / `stale_vs_storyline`(252) / S5 人改率(253) / storyline CLI(255) / `--no-edit-warn`+`project list`(256) / `signals`(257)；质量门(245)、db-maintenance 根因(246) |
| **包版本** | 仍是 `0.5.0`（不 bump） |
| **里程碑** | **M0–M4 代码验收全量 PASS；tech-m4 §9 四项全清零；post-M4 路线方向 A/C/B 闭环**（均 2026-11-13）；回归基线 3654 passed / 2 skipped / 1 xpassed |
| **进行中** | task 258 dogfood——助手侧 runbook + 复盘模板已备（`.tmp/dogfood-w2.sh`），**等 owner 执行**（预算 ¥3） |
| **下一闸门** | ① owner 执行 dogfood 并填复盘；② push 决策；③ S7 预算线定义（signals 的「对预算完成率」待拍板） |
| **本 handoff** | post-M4 三方向 + review 修复轮（1C+4I+5M）全闭环；`tests/cli` 315 全绿（doctor flake 已根修） |

硬约束（接手期间同样适用）：

- 不声称 V1.0 完成；不升包版本；不合成大 PR。
- 不改结算权威；结算库仍是 `untrusted_until_confirmed` 对照，不升格 Canon。
- `review`（task 241）只读共审：B8 七源并集、零写库、复读/专名启发式；review 发现问题 exit 0（B11）。
- 不加题材检查器；不跑无人值守长篇。
- 编码刀仍建议 TDD + 审阅后再合；小步 PR。

## 一眼进度

| 里程碑 | 状态 | tip / 证据 |
|--------|------|-----------|
| M0 只读工作台 | **PASS** | `80f4107` · [204](../tasks/done/204-m0-acceptance.md) |
| M1 人确认 + `check` | **PASS** | `69d7ece` · [210](../tasks/done/210-m1-acceptance.md) |
| M2 标脏 / 承诺 / extract→pending | **PASS** | `f1c3093` · [218](../tasks/done/218-m2-acceptance.md) |
| M3 技术方案 [tech-m3.md](tech-m3.md) | **已接受**（t104s937；B1–B7 原样） | #55 → `5101555` |
| M3 步 1–6 抽卡表面 | **已在 `main`** | 功能 tip `1b0e323`（#56–#60）；步 6 闭环文案 task 233 |
| M3 §6–7 代码验收 | **PASS** | `594144b` · [234](../tasks/done/234-m3-code-acceptance.md) |
| M4 技术方案 [tech-m4.md](tech-m4.md) | **已接受**（2026-11-08；B1–B12 原样） | `dd25f30` |
| M4 步 1–5 W2 短环 | **已在 `main`** | 238 `c55a714` · 239 `f205f8a` · 240 `23bd3f3` · 241 `b857e8b` · 242 `e5a33bd` |
| M4 §6–7 代码验收 | **PASS** | `e5a33bd` · [243](../tasks/done/243-m4-code-acceptance.md) |
| task 244 冒烟 P1 修复 | **DONE（切片 5 真实模型复验 PASS）** | 代码 @ `120012c` · [244](../tasks/done/244-修复抽卡死锁与圣经空渲染.md)（复验 ¥0.4823：死锁解除、圣经 0→1664 字、抽卡真实正文、stale 置 1） |

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

M4 步 1 章进度视图 + `status`（task 238；tech-m4 §5 步 1）：

```text
songyan status --project-id TEXT [--json]
```

- 纯只读项目级计数面：章进度六态分布（章宇宙 = heads ∪ variants ∪ versions 章号并集；`stale`/`settled` = accepted ± `content_stale`，`picked` / `variants_ready` / `drafting` / `empty`）+ 待确认 picked 数 + ContextEmergency 触发次数 / 最近触发章 / `budget_used_before_emergency`（B10）。
- `today` 文本与 `--json` 同步增加 `chapter_progress` 摘要行（下一章 = B1 口径第一个非 accepted 章）；`_NEXT` 文案在 task 242 更新为 M4 口径（continue 短环 + 抽卡提示）。
- exit 0 / 1（缺库缺项目）；usage 错误 exit 2（B11 口径）。`chapter status` 不做。

M4 步 2 `chapter accept`（task 239）/ 步 3 `chapter continue`（task 240）：

```text
songyan chapter accept   --project-id TEXT --chapter INT [--from-file PATH] [--json]
songyan chapter continue --project-id TEXT [--count 1] [--variants N] [--require-plan] [--json]
```

- accept：单事务仅 accepted 副本 + head 双指针（B5 拆开；不跑 settlement、不动 `plan_*` / variant 行）。
- continue：B1 目标章 = 第一个非 accepted 章（步 1 视图同口径）；两前置 exit 2（之前存在 picked 未 accept 的章 / 目标章已有未确认工作稿；无自动重生成旗标）；空项目 / 全 accepted exit 0 提示。
- 准备阶段（B5）：上一章 accepted 未 settlement（`summaries` 无该章记录 **且** `character_states.source_version_id` 无该版本行的复合判定）→ 补跑 extract + apply + summaries 行（RAG / lifecycle / SettingEvaporator 不进本步序列）；只产 `plan_*` pending 提案，approved 集不变。
- B6 衔接段：上一章 accepted 正文结尾 ≤800 字经 `workflows/_helpers.assemble_context_package` 新增 `last_chapter_ending` 透传（默认空串 = `run` 行为不变）+ 既有 120 字 `plot_summary` 注入；`chapter_goal` 无行 → `words_per_chapter` 兜底；brief 缺失 `None` 继续。
- B7：`--variants N` 函数级转调 `generate_chapter_variants`（M3 语义原样：不 auto-pick、不写 `plan_*`）。
- B9 run 壳：单章壳（`chapter_range_start == end == 目标章`）；收养仅限 status ∈ running/paused 的匹配单章壳（engine 多章壳不收养）；LLM 失败 / 预算熔断 → `paused` + `pause_reason`，再 continue 续跑只追加新版本。
- exit（B11）：0 = 生成待确认 / 停闸 / 全部完成；1 = 缺库 / 缺项目 / 参数非法（`--count` 越界）/ LLM 与 settlement 失败；2 = B1 两前置 / `--require-plan` 拒绝；3 = 预算耗尽（已写保留）。`--count N` 逐章停闸，单次 invocation 最多生成一章。
- 费用归因：全程 `bound_contextvars(project_id, chapter_number, run_id, agent)`；`--json` 含 `chapter / version_id / word_count / cost_cny / next_hint`。

M4 步 4 `songyan review`（task 241；tech-m4 §5 步 4）：

```text
songyan review --project-id TEXT --chapter INT [--json]
```

- 只读共审：被审正文 = current 工作稿；七源聚合（B8）；复读三腿阈值 12/40/14 与专名漂移为 info 级启发式，不阻塞。
- 零写库：12 表行数不变断言 + `merge_reviews` 未调用；approved 行数不变（PRD :501）。

既有管线仍可用：`create-project` / `run` / `report` / `import` / `doctor` / `backup` 等（`run --auto-confirm` 是冒烟路径，**不是**作者主路径）。

## 接手开发时先看这些

| 目的 | 文件 |
|------|------|
| 产品边界 | [prd-v1.md](prd-v1.md) |
| M3 做什么 / 不做什么 / 小步定义 | [tech-m3.md](tech-m3.md)（尤其 §3、§4、§5） |
| M4 做什么 / 不做什么 / B1–B12 | [tech-m4.md](tech-m4.md)（尤其 §3、§5、§6） |
| 当天下一步（给助手） | [HANDOFF-mew.md](HANDOFF-mew.md) |
| 冷启动规则 | [AGENTS.md](../AGENTS.md) |
| CLI 入口 | `src/songyan/cli/commands/variant.py`、`canon_write.py`、`workbench.py`、`check.py`、`chapter.py`、`review.py`、`status.py` |
| M3 服务 | `src/songyan/services/variant_{fingerprint,generate,diff,pick,stale}.py` |
| M3 仓库 | `src/songyan/db/chapter_variant_repo.py` |
| M4 服务 | `src/songyan/services/chapter_{accept,continue}.py`、`review_report.py`、`chapter_progress.py` |
| 步 5 归档 | [tasks/done/224-m3-step5-stale-cost.md](../tasks/done/224-m3-step5-stale-cost.md) |
| 本地回归（抽卡相关） | `tests/cli/test_variant_*.py`、`tests/services/test_variant_fingerprint.py`、`tests/db/test_chapter_variants.py` |
| 本地回归（M4 相关） | `tests/cli/test_chapter_*.py`、`tests/cli/test_review*.py`、`tests/cli/test_status_command.py`、`tests/services/test_review_report.py` |

本地仓库路径（Diupi-Yun）：`C:\Vibe Project\Songyan`；origin/main 随本页提交 push 后同步（此前 @ `8da4cd0`）。

## 已知限制

- 只有 CLI，不是托管服务。真实生成要 API key，并且花钱。
- **升级后先跑 `songyan doctor --init-db`**：窄加列迁移（quality_flag / stale_vs_storyline 等）只在 init/doctor 路径执行；直接对旧库跑 list/status 会以 IndexError 提示缺列（2026-11-13 真实库核对实证，既有契约非新缺陷）。
- 《轨道蜃景》Ch1–10 管线曾 PASS、文学未过（DG-1 失败等）；细节见历史冒烟记录，不作 V1.0 文学验收。
- 真实模型上「导入后再续写」还没有验收。
- **未做：** 真实模型冒烟（维护者任务，不挡代码验收）；M4 之后事项（`chapter status` / `review --deep` / 导入后再续写验收）属 tech-m4 §9「以后」清单，需 owner 新授权立项。
- `today` 的固定 `next` 文案已更新为 M4 口径（提示 `chapter continue` 短环 + `variant generate` 抽卡；task 242，2026-11-09）。
- **2026-11-07 评审修复（task 226，已归档 `tasks/done/`）**：全量 code review 的 1 blocker + 4 major + minor 批已修复——settlement 声称的伏笔 resolve 只进提案（不再直写 `resolved`；唯一写径 = `canon confirm promise`）；`variant generate` 成本记账去重且归因 project/agent；pick 拒绝 abandoned 槽；LLM 失败保留已写槽并报 stderr；rejected 行不可被 confirm 直接转正；extract 提案跳过 rejected。详见 `tasks/done/226-review-findings-fix.md` 与 `docs/superpowers/plans/2026-11-07-m0-m3-review-audit.md`。
- **2026-11-07 审计补强（task 228，已归档 `tasks/done/`）**：`canon confirm promise` 的人证 evidence 落库（`foreshadowings.resolved_evidence`，写-only 审计列）；销账守卫与写入合并为原子 UPDATE（并发双销账恰一成交）。读口径与 open 集不变。
- **2026-11-08 P0-3 收口（task 232，已归档 `tasks/done/232-plan-default-pending.md`）**：plan 五模型 `approval_status` 默认值 `"approved"` → `"pending"`（owner 拍板方案 A）。不显式传状态构造的卡从此落入 pending 队列，不再静默直写 Canon；生产写入方与种子夹具本就显式传值，零行为变化。测试侧 26 处夹具语义卡显式补 `approved`，新增模型级默认行为锁。
- **环境项（2026-11-08 修复，task 235；2026-11-09 根因修正）**：~~`test_llm_http_timeout`~~ 断言窗口 8s→20s（hold 15s→30s 保判别性）。**根因修正**：该测试当天的「通过」多为假通过——`ChatLiteLLM` 无 `base_url` 字段（只有 `api_base`，extra=ignore 静默丢弃），请求实际落到 litellm 默认地址；上午断网时 ConnectTimeout 恰好匹配「超时」断言。2026-11-09 网络恢复后 401 暴露真相，已在 task 239 修复（`api_base=base_url` + 防回归断言）；负载敏感性结论作废。~~`test_191_ch200_harness.py`~~ `_run_harness` 双端固定编码（父 `encoding="utf-8"` + 子 `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8`），不带 PYTHONUTF8 也绿。本机全量回归不再需要 `PYTHONUTF8=1`。
- **2026-11-08 M4 前置调研（task 236，已归档 `tasks/done/`）**：`docs/236-m4-preresearch.md` 交付——四路调研（PRD 需求 / 代码现状 / 历史审计 / 外部同类工具）+ 四大设计问题深化（chapter 状态机、continue↔variant、review 输入并集、ContextEmergency 露出）+ 新问题 N1–N7（含 import replay 自动 accepted 写径与 M4 确认闸的并存口径）。
- **2026-11-08 M4 技术方案（task 237）→ 2026-11-09 M4 全量闭环（task 243）**：`docs/tech-m4.md` 已接受（owner 拍板「接受 tech-m4，按 B1–B12 开 M4 编码」）；步 1–5 全部落地（238–242）；**§6–7 代码验收 PASS @ `e5a33bd`**（8 条证据映射见 task 243；实跑数见 task 242 完成总结）。文档层偏差记录：tech-m4 §7 引用的 `tests/cli/test_chapter_continue.py` 已拆为五个 `test_chapter_continue_*` 文件，以实际文件名跑。
- **2026-11-11 真实模型冒烟（`.tmp/smoke-m4-20261111/`，不入库）**：W2 短环管线在 DeepSeek 真模型下 PASS（`run` / continue 单稿与 --variants / accept / review 零写库 / status / today / check，费用 ¥0.7747 / 41 次调用）；暴露 2 个 P1（发现 5：pick→accept 后 continue 对后续章永久 exit 2 死锁——B1 前置①按 variant 行级判定误伤 accepted 章残留槽，而 abandon 又拒绝 picked 槽；发现 6：`_render` 无 events/clues 即空串 + 实体仅 event 引用入选，导致 extract→confirm 流的实体/属性型 Canon 圣经文本恒空、抽卡必产垃圾）。**task 244 修复已进 main @ `120012c`**（B1 前置①章级化；圣经入选 R1 + 渲染去早退；空项目/全 accepted 分文案；全量 3598 passed + ruff 绿）；切片 5 真实模型复验进行中。遗留（未立项）：发现 3/4 写手拒写/占位不判失败与重试策略（需产品决策）；`run` 收尾 `db_maintenance_failed: database table is locked`（Windows + memory checkpointer，非阻塞）。
- **2026-11-12 变体拒写质量门（task 245，已归档 `tasks/done/`）**：真实模型冒烟发现 3/4 修复——`classify_variant_draft` 纯函数（<100 字兜底 +「（空）」/拒写关键词硬信号，>500 字不查防长文台词误伤）；拒写槽同槽自动重试 1 次（注入坚持指令）后落槽打 `quality_flag`；`variant list` 露出、`variant pick` 拒绝打标槽（exit 2）；全败 exit 2 / 部分成功 exit 0 列失败槽；`chapter_variants.quality_flag` 幂等迁移。代码 @ `8c26105`；全量 3618 passed + ruff 绿；真实模型复验 ¥0.3491 / 20 次调用（空圣经与 confirm 后两场景均零误伤）。遗留：task 246（run 收尾 db-maintenance 锁表）转 DOING；§9「以后」清单未立项；2 个既有 flake（doctor 子进程 / canon promise 并发，与本案无关）。
- **2026-11-12 db-maintenance 锁表修复（task 246，已归档 `tasks/done/`）**：真实 run 收尾 `database table is locked`（Windows 3/3 必现）根因实锤——`get_db()` 的 `PRAGMA quick_check` 从不消费结果，prepare 期启动的完整性扫描持锁悬挂，同连接后续 `wal_checkpoint` 吃 SQLITE_LOCKED。修复：quick_check 结果取尽 + 游标关闭（RES-03 从此真正执行）；防御层：维护分步容错 + checkpoint busy 行落日志（原从不 fetch、busy 被静默吞掉）+ TRUNCATE 失败回退 PASSIVE。最终实测收尾 0 告警、WAL 截断 0 字节（¥0.4203）；全量 3623 passed + ruff 绿。
- **2026-11-12 tech-m4-followup 落地中**：方案 `docs/tech-m4-followup.md`（B1–B8）已接受（「开工」@ `928de90`）。**步 1 `chapter status` 已交付**（只读章进度面；tests/cli 8 新测全绿）。**步 2 导入后再续写验收 PASS（task 249，2026-11-13，¥0.4995）**：import replay 自动 accepted 与零自动 Canon approved 分列验证；imported 项目 continue 单稿 3048 字 + 抽卡两槽全通；零代码修改。**步 3 `review --deep` 已交付（task 250，2026-11-13）**：显式 LLM 深审（成本前置交互门 + --yes + --budget-cny，非 TTY 无 --yes 拒绝 exit 2）；三件套输入四口径，findings 与七源同形合并；零写库，agent=review.deep 归因。全量 3631 passed + ruff 绿；真实模型复验 4 findings 全带原文证据，预估 ¥0.0166/实花 ¥0.0107。**tech-m4-followup 三步全部闭环，§9 清零**（S5 产品向项除外）。
- **2026-11-13 tech-m4-followup-s5 落地中**：方案（B1–B8）已接受（「按照目前方案开工」@ `f3d5403`）。**项 ① `stale_vs_storyline` 已交付（task 252）**：故事线切片指纹（全书 outline + 覆盖弧含边界 + 相关线索三条件并集）驱动独立新鲜度标记，与 stale_vs_canon 完全隔离（PRD「故事线不是 Canon」红线三不混：分表/分指纹/分标记）；旧行升级不标脏、只标不消；list/status 露出、pick 软提醒不拦。**项 ② S5 人改率警告已交付（task 253，2026-11-13）**：accept 现算行级 edit_ratio（<5% stderr 所有权提醒，exit 0 不拦，--json 露字段，不落表）；chapter status 现算露出；--from-file 口径上溯一级比原工作稿。**tech-m4-followup-s5 两项闭环，tech-m4 §9 全部清零（含 S5 产品向项）。**全量 3654 passed / 2 skipped / 1 xpassed + ruff 绿。
- **2026-11-13 post-M4 路线落地中**：路线（`docs/tech-roadmap-post-m4.md`）与技术方案（`docs/tech-post-m4.md` v2）已接受。**方向 A storyline 编辑 CLI 已交付（task 255 @ `657d019`）**：`storyline show|edit|remove` 命令族（直写+审计表+软删 archived+窄校验 exit 2），故事线切片指纹排除软删行（252 标脏联动入口打通）。方向 C（256）进行中；B（257）排队；D dogfood（258）并行。
- **2026-11-13 post-M4 方向 C 质量小项交付（task 256 @ `f9d84e2`）**：`chapter accept --no-edit-warn`（PRD :473「可以关掉」）+ `project list`（:559）。**既有 flake 清账**：doctor 子进程测试根因 = Windows 子进程 GBK 管道编码（修后三连稳）；canon promise 并发 flake 五连不复现、留观察。方向 B（257）进行中。
- **2026-11-13 post-M4 方向 B S 信号交付（task 257 @ `0e0cfc8`）**：`chapter_heads.edit_ratio` 落列 + 独立 `songyan signals` 命令（S1/S3/S4/S5/S7 口径单测；S2 冲突关闭周期 gap 明示——需 owner 决定是否立冲突记账面）。**tech-post-m4 三方向（A/C/B）全部闭环**；tests/cli 306 全绿（doctor flake 修复后首次零失败）。余 258 dogfood（owner 侧）。 **2026-11-13 整体 review 一轮**（子代理审查 + 零 API 场景测试）：修复软删生命周期三连环（C1）、S7 每章成本口径、project list settled、signals 未迁移库守卫等 1C+4I+5M @ `7cfb91b`/`4f6a0a9`；全量 3654 passed。M3/F1 已闭环（remove 不存在 id 钉死 exit 2 同族口径；省略 --arc-index 自动分配 max+1 并回显）。遗留待 owner：S7 预算线定义。 258 助手侧 runbook + 复盘模板已备（`.tmp/dogfood-w2.sh`），等 owner 执行（预算 ¥3）。

标识与助手交接：[HANDOFF-mew.md](HANDOFF-mew.md)。书稿不入库。

## 文档

| 文件 | 用途 |
|------|------|
| [README](../README.md) | 访客概览 |
| [AGENTS.md](../AGENTS.md) | 冷启动：读什么、何时不许写代码 |
| [prd-v1.md](prd-v1.md) | V1.0 产品需求（已接受） |
| [tech-m0.md](tech-m0.md) / [tech-m1.md](tech-m1.md) / [tech-m2.md](tech-m2.md) | 已验收里程碑方案 |
| [tech-m3.md](tech-m3.md) | 抽卡；已接受；步 1–6 已落地；§6–7 PASS（`594144b`） |
| [tech-m4.md](tech-m4.md) | W2 短环；已接受（B1–B12 原样）；步 1–5 已落地；§6–7 PASS（`e5a33bd`） |
| [ADR-0001](adr/0001-plan-first-facts.md) | 事实由计划和人写入 |
| [INDEX](INDEX.md) | 文档地图 |
| [quickstart.md](quickstart.md) | 安装短窗口 |

## 维护者下一步

1. **当前 tip `e5a33bd` + 本页文档提交（push 后 origin 同步）。** M0–M4 代码验收全量 **PASS**；PRD 内里程碑全部闭环。下一闸门 = 真实模型冒烟（维护者任务，花真钱）；「以后」清单（tech-m4 §9：`chapter status` / `review --deep` / 导入后再续写验收）需 owner 新授权立项。
2. 不改结算权威；不大 PR；不 bump；不声称 V1.0 完成。
3. owner 本地接手期间：以本页 + tech-m3 / tech-m4 为准；助手侧默认待命，不抢开「以后」清单。

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

# tech-post-m4 · 方向 A/C/B 技术方案（storyline CLI / 质量小项 / S 信号）

| 项 | 内容 |
|---|---|
| 状态 | 草稿（task 255–257，2026-11-13）——路线 B1–B7 已接受；**本文待 owner review 后按方向开工** |
| 关联 | `docs/tech-roadmap-post-m4.md`（路线，已接受 2026-11-13）；PRD :17/:48/:473/:559/§5.2；task 252（stale_vs_storyline 联动）/ 253（S5 现算） |
| 范围 | 一案三项（仿 tech-m4-followup 模式）：**A storyline 编辑 CLI（task 255）→ C 质量小项（task 256）→ B S 信号（task 257）**；D dogfood（task 258）为 owner 侧并行项，见 §D |

路线已定决策（原样继承，不再重开）：D 并行 + A → C → B；故事线直写 + 审计（B2）；软删（B3）；`--no-edit-warn`（B4）；S5 落 chapter_heads 窄列（B5）；signals 挂 `report`（B6）；project list 只做 list（B7）。

---

## §A · storyline 编辑 CLI（task 255）

### A.1 命令面（挂新 `storyline` 组，与 `canon` 族同形）

```
songyan storyline show --project-id TEXT [--json]
songyan storyline edit outline --project-id TEXT [--core-conflict T] [--mainline-synopsis T]
                                 [--themes JSON] [--intended-ending T] [--json]
songyan storyline edit arc --project-id TEXT --arc-id TEXT [--arc-index N]
                           [--start-chapter N] [--end-chapter N] [--arc-goal T]
                           [--open-thread ID ...] [--resolve-thread ID ...] [--json]
songyan storyline edit thread --project-id TEXT --thread-id TEXT [--title T] [--description T]
                              [--status planned|opened|advanced|resolved|abandoned]
                              [--opened-chapter N] [--expected-resolve-arc N] [--json]
songyan storyline remove arc --project-id TEXT --arc-id TEXT [--json]
songyan storyline remove thread --project-id TEXT --thread-id TEXT [--json]
```

- `edit` = upsert（outline 全书一行；arc/thread 按 id 存在即更新、不存在即建），与 `canon edit` 同形。
- `show`：文本复用 workbench 故事线分面；`--json` 结构化（outline/arcs/threads 三键，archived 行标注）。

### A.2 数据面

- **审计表** `storyline_edit_history`（B2，仿 `genre_runtime_profile_history`）：`history_id / project_id / target_type(outline|arc|thread) / target_id / action(create|update|remove) / before_json / after_json / created_at`。每次 edit/remove **与目标行同事务**写审计。
- **软删**（B3）：`arc_plans` 与 `plot_threads` 各加 `archived INTEGER NOT NULL DEFAULT 0`（窄迁移，幂等）。remove = archived=1，不物理删；plot_threads 的 `status` 状态机不动（archived 是独立维度）。**指纹选择排除 archived**（`load_storyline_slice` 两处过滤）——软删故事线元素 = 该章故事线切片变化 → 252 懒标定自动生效。
- 被软删弧的 `threads_to_open/resolve` 引用、threads 的 `expected_resolve_arc` 指到 archived 弧：保留不动（历史语义），因 archived 弧不再进覆盖集，天然失效。

### A.3 校验与 exit 码（B11 同形）

- 0 = 成功；2 = 业务拒绝：`start_chapter > end_chapter`；`--open-thread/--resolve-thread` 引用不存在的 thread_id；`--expected-resolve-arc` 指向不存在的 arc_index（**拒绝而非静默**，窄检查薄封装）；1 = 缺库/缺项目/参数非法。
- 词汇纪律：这是规划面编辑，文案不出现「入典/Canon」字样。

### A.4 测试口径

CRUD + 审计行同事务断言；非法引用 exit 2；软删后：指纹排除（复用 252 切片断言风格）、list 故事线标注 archived、`remove` 幂等（重复 remove exit 0）。

---

## §C · 质量打磨小项（task 256）

### C.1 `chapter accept --no-edit-warn`（B4 / PRD :473）

- 旗标跳过 253 的 stderr 警告；`--json` 输出字段不变（edit_ratio 照常露出）。
- 测试：带旗标无警告；不带照常；与 `--from-file` 组合。

### C.2 `songyan project list`（PRD :559 之一）

- 输出每项目：project_id / title / genre / mode / lifecycle_status / 章宇宙规模（heads 数）/ settled 数。`--json` 同形。
- `ProjectRepository.list_projects()` 新方法（简单 SELECT；不碰其他仓库）。
- exit 0；空库输出空表（exit 0）。**不做** `new/init` 别名（B7）。

### C.3 两个既有 flake 修复

- `test_doctor_subprocess_reports_invalid_checkpointer_without_traceback`：本机干净树复现 → 先调查（子进程 env 传播 / Windows 路径形态 / checkpointer 校验时序）再修；修不动则改测试隔离方式并在任务文档记录结论。
- `test_confirm_promise_concurrent_double_settle_guarded`：时序加固（等待条件而非固定 sleep；或显式串行化断言）。
- 验收：各双跑 ≥3 次稳定。

---

## §B · S 信号度量面（task 257）

### B.1 S5 落表（B5）

- `chapter_heads.edit_ratio REAL` 窄列（迁移幂等；历史行 NULL = 未记，**不回填**）。
- `accept_chapter` 事务内随 head upsert 写入（现算值已在 253 就绪；run 管线 auto-confirm 路径不在本列范围——S5 是人的所有权信号）。
- `chapter status` 优先读列，NULL 时回落现算（253 口径），保证旧项目可读。

### B.2 `report` 加 signals 分区（B6）

每信号注明**数据源 → §5.2 口径映射**；拿不到口径所需数据的信号显式标 `gap`，不编造：

| 信号 | 计算 | 数据源 |
|---|---|---|
| S1 周确认数 + dismiss 比 | 近 7 天 approval_status 变迁（updated_at 落在窗口的 approved 计数；dismiss 比 = rejected/(approved+rejected) 全量） | plan_* 五表 |
| S3 开放伏笔年龄 P50 | open 伏笔（`foreshadowings.status` open）当前章 − 植入章的 P50 | foreshadowings + 当前进度章 |
| S4 抽卡采纳分布 | 全项目 picked 槽的 slot_index 分布（含「全是 1 号」塌缩提示文案，PRD：先查塌缩不加 N） | chapter_variants |
| S5 人改率分布 | edit_ratio 列的分布（NULL 占比注明；均值 + <5% 占比） | chapter_heads.edit_ratio |
| S7 单章成本 | 每章 llm_call_usage SUM 对 words_per_chapter 预算的完成率（口径 ¥2/M in / ¥8/M out 已是估算值，照录） | llm_call_usage |
| **S2 冲突关闭周期** | **gap**：现网无冲突记账面（open→closed/dismiss 无时间序列表），需 owner 决定是否立小记账面，本任务不做 | — |

- 渲染：文本分区 + `--json` 的 `signals` 键；today 不动（B6）。

### B.3 测试口径

每信号一个口径单测（构造数据 → 断言数值）；gap 信号断言输出含 `gap` 标注；S5 列与现算一致性断言。

---

## §D · dogfood（task 258，owner 侧并行）

助手交付 `.tmp/dogfood-w2.sh`（造项目 → 逐章 W2 循环 → canon confirm 批处理 → 费用归因，沿用 249 runbook 模式）+ 复盘模板（摩擦清单：现象/频率/建议方向）。owner 执行（预算 ¥3），复盘项转立项须再拍板。

---

## 验收标准（分列）

- **A**：A.4 全绿；审计同事务；软删指纹排除；全量回归 + ruff 绿。
- **C**：:473 满足；project list 口径对；flake 双跑 ≥3 稳定；全量回归 + ruff 绿。
- **B**：五信号口径单测全绿 + S2 gap 明示；S5 列/现算一致；全量回归 + ruff 绿。
- 共同：不 bump；不声称 V1.0；每任务完工同步 STATUS/HANDOFF 并归档。

## 不做（三方向共同红线）

题材检查器 / 自动选优 / 「可发表」声称 / S9 文学自动门 / storyline 硬删 / `project new|init` 别名 / S2 编造或多立记账面（须 owner 另行拍板）。

---

## 接受注记

（待 owner review：可对单方向点名修改；确认后按 A → C → B 顺序开工，D 并行。）

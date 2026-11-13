# tech-m4-followup-s5 · 故事线 × 变体新鲜度 + S5 人改率警告

| 项 | 内容 |
|---|---|
| 状态 | 草稿（task 251，2026-11-13）——**待 owner 书面接受后才拆编码任务** |
| 关联 | tech-m4 §9 第四项（「故事线纳入 fingerprint / 人几乎不改就标 settled 的警告（S5 产品向）」）；PRD :200 S5 信号、:638 所有权风险行、:108「故事线不是 Canon 的别名」红线；task 244（fingerprint 语义恢复 @ R1） |
| 范围 | 两项：**① 故事线与变体新鲜度耦合（独立 `stale_vs_storyline`）** + **② `chapter accept` 人改率警告（S5）**。owner 已预拍板：①独立标记 + 本章相关切片粒度；②stderr 警告 + JSON 字段、不落表、阈值 5% 硬编码 |

tech-m4 §9 原文口径（本文不越出）：「故事线纳入 fingerprint / 人几乎不改就标 settled 的警告（S5 产品向）」。§9 其余三项已由 task 248–250 闭环。

---

## 1. 结论速览

| 项 | 交付 | 写库 | 对既有语义影响 |
|---|---|---|---|
| ① stale_vs_storyline | 变体行新标记 + 懒刷新 + list/status/pick 露出 | 变体表两新列（标脏/指纹），无新表 | parent_canon_fingerprint / stale_vs_canon **零改动**；M3 三态不变 |
| ② S5 人改率 | accept 时现算 edit_ratio，<5% stderr 警告 + `--json` 字段 | 不落表 | accept 事务零改动（纯读取计算）；exit 0 不拦 |

**红线自检**：PRD :108「故事线不是 Canon 的别名——分表存放，分开展示」——本文保持三不混：分表（不并 plan_*）、分指纹（storyline_fingerprint 独立）、分标记（stale_vs_storyline 独立）。作者改故事线**不会**污染 Canon 语义，反之亦然。

## 2. 现状面（事实清单，证据 = 文件:行号）

### 2.1 fingerprint 面

- `variant_fingerprint.py:1-6` 模块注释明文：输入 = 本章可见 approved Canon（同 `load_chapter_plan_bible` 口径），「Pending / rejected / body / **storyline** are excluded」。
- 指纹消费方：`variant_generate`（slot 落 `parent_canon_fingerprint`）、`refresh_stale_vs_canon`（`variant_stale.py:21-49`，list/diff/pick/generate 前懒标，只标不消）。
- 故事线三张表（`story_outlines` / `arc_plans` / `plot_threads`，迁移 `migrations.py` 内 _migrate_narrative_skeleton）有独立写径：模板播种（create-project）、`outline_import` 文件导入、goal_planner 代理——**改动故事线 Currently 对变体新鲜度零影响**：作者调了大纲，已 pick 的槽照常 `stale_vs_canon=0`，无任何信号。

### 2.2 故事线模型面（`models/narrative.py`）

- `StoryOutline`：core_conflict / mainline_synopsis / themes / intended_ending（**全书一行**，改它 = 全书级事件）。
- `ArcPlan`：start/end_chapter / arc_goal / threads_to_open / threads_to_resolve / is_mainline。
- `PlotThread`：title / description / status / opened_chapter / expected_resolve_arc（arc_index）/ last_status_*。

### 2.3 accept 面

- `chapter_accept.py:58-152`：确认时 `accept_version` 复制 current（或先物化 `--from-file` edited 行，`parent_version_id` 指向原稿）→ accepted 副本。**无任何 diff/人改率计算**。
- PRD :200 S5 =「pick 之后工作正文相对原稿的 diff 非空比例——所有权代理，不是文学分」；PRD :638 所有权风险行：「M4 可警告『几乎没改』」。两处都是**警告级**，不是闸门。

## 3. ① stale_vs_storyline 设计

### 3.1 数据面（chapter_variants 两新列，幂等迁移仿 task 245 quality_flag）

| 列 | 类型 | 语义 |
|---|---|---|
| `stale_vs_storyline` | INTEGER NOT NULL DEFAULT 0（0/1） | 相对故事线演进的新鲜度；只标不消 |
| `storyline_fingerprint` | TEXT NULL | generate 时记录的本章故事线指纹；NULL = 旧行（未评估） |

### 3.2 本章相关切片指纹（owner 已拍板粒度）

`storyline_fingerprint(project_id, chapter) -> sha256`（纯函数 + canonical JSON，仿 `parent_canon_fingerprint`）：

- **全书层**：`story_outlines` 行（无行 → 空 dict）。core_conflict / mainline_synopsis / themes / intended_ending 任一改动 = 全书所有章指纹变（合理：这是全书级事件）。
- **覆盖本章的弧**：`start_chapter <= ch <= end_chapter` 的 ArcPlan；取 arc_id / start / end / arc_goal / threads_to_open / threads_to_resolve / is_mainline。**边界字段进指纹**——移动弧边界使本章跌出/落入弧，指纹变化即标脏，语义正确。
- **相关线索**：并集三条件——① thread_id ∈ 覆盖弧的 open/resolve 列表；② opened_chapter 非空且 ≤ ch；③ expected_resolve_arc 指向覆盖本章的弧。取 thread_id / title / description / status / is_mainline / opened_chapter / expected_resolve_arc。

### 3.3 懒刷新（与 stale_vs_canon 同触发点）

`refresh_stale_vs_storyline(project_id, chapter)`，在 list / diff / pick / generate 前与既有刷新并列调用：

- 每行：`storyline_fingerprint` 为 NULL（旧行）→ **只补记指纹，不标脏**（B3：升级不全书标脏）；非 NULL 且 ≠ 当前值且 `stale_vs_storyline=0` → 标 1；同时把过期指纹补记为当前值（含已标脏行，保持同步）。
- 只标不消（B4：清脏 = 新 generate 行带新指纹，语义同 stale_vs_canon）。
- `variant_generate` 生成行时写 `storyline_fingerprint = 当前值`、`stale_vs_storyline = 0`。

### 3.4 露出与行为

- `variant list`（JSON + 文本）与 `chapter status` 槽分区加 `stale_vs_storyline`。
- `variant pick`：**默认不拦**（B5 推荐：软信号区别于 Canon 级 stale）；目标槽该标记 =1 时 stderr 提醒「该槽基于已演进的故事线草稿，请人工斟酌」，exit 0 照旧。
- exit 码全不变。

## 4. ② S5 人改率警告设计

### 4.1 计算口径

- **edit_ratio = 变更行数 / max(源稿行数, 1)**，变更行数取 difflib opcodes 的 insert+delete 行数（replace 计两侧行数）。
- 源稿对：无 `--from-file` → 源 = `head.current_version_id` 工作稿（accepted 副本为纯复制 → edit_ratio=0，正是「直接采纳抽卡」场景）；有 `--from-file` → edited 物化行 vs 原工作稿（`parent_version_id` 链现成）。
- 阈值硬编码 `_EDIT_WARN_THRESHOLD = 0.05`（owner 拍板：不参数化）；edit_ratio < 阈值（含 0）触发警告。

### 4.2 呈现（警告级，零闸门）

- `accept_chapter` 现算（事务外读取计算，事务本身零改动），`AcceptOutcome` 加 `edit_ratio: float`。
- CLI：`chapter accept` 触发时 stderr 打印——「人改率 x.x%：本章几乎未改动工作稿即确认——所有权提醒（S5），不影响确认」；`--json` 输出含 `edit_ratio`。exit 0 不拦。
- `chapter status` 对 settled/stale 章现算露出人改率（accepted.content vs source_version content，同口径）。
- **词汇红线**：只说「几乎未改动/所有权提醒」，不评质量、不评「好不好」（AGENTS.md 纪律）。

## 5. B 决策点（逐条拍板）

| # | 决策点 | 口径 | 备注 |
|---|---|---|---|
| B1 | 独立两列（stale_vs_storyline + storyline_fingerprint），parent_canon_fingerprint / stale_vs_canon 零改动 | §3.1 | 防 Canon 语义被故事线污染 |
| B2 | 本章相关切片（全书 outline 行 + 覆盖弧 + 相关线索，字段白名单 §3.2） | §3.2 | 已预拍板 |
| B3 | 旧行（指纹 NULL）首次刷新只补指纹不标脏 | §3.3 | 升级不全书标脏 |
| B4 | 只标不消；清脏 = 新 generate 行 | §3.3 | 同 stale_vs_canon 语义 |
| B5 | pick 默认不拦 stale_vs_storyline，stderr 软提醒 | §3.4 | 要拦需显式改本条 |
| B6 | S5 行级变更率、阈值 0.05 硬编码、stderr 警告 + accept --json edit_ratio、不落表 | §4 | 已预拍板 |
| B7 | variant list / chapter status 露出两个新字段 | §3.4/§4.2 | — |
| B8 | 不做：不评文学质量 / accept 不因此被拦 / 不落 S5 表 / 不动 Canon 指纹与任何 Canon 写径 / 故事线不加章窗口外语义 / 不做「自动改稿建议」 | — | 红线照 AGENTS.md 与 PRD :638 |

## 6. 验收标准（分列两项）

- **①**：切片指纹单测（覆盖弧边界移动 / 无关弧改动不标脏 / 全书 outline 改动全书标脏 / 旧行只补指纹）；懒刷新只标不消；generate 落指纹；list/status/pick 露出与提醒；pick 不被拦（exit 0）；全量回归 + ruff 绿。
- **②**：edit_ratio 口径单测（纯复制 =0；改一行 >0；--from-file 对原稿）；<5% stderr 警告 + JSON 字段；≥5% 无警告；accept 事务零改动（九表断言不破）；chapter status 露出；全量回归 + ruff 绿。
- 共同：不 bump 版本；不声称 V1.0；STATUS/HANDOFF 同步；归档 `tasks/done/`。

## 7. 小步任务拆分（接受后）

| 任务 | 内容 | 依赖 |
|---|---|---|
| 252 | ① stale_vs_storyline（列 + 切片指纹 + 懒刷新 + generate 记录 + list/status/pick 露出） | 无 |
| 253 | ② S5 人改率（accept 现算 + 警告 + JSON 字段 + status 露出） | 无（可与 252 并行） |

## 8. 风险与开放问题

- **故事线写径少**（模板 / outline_import / goal_planner）：人手动调故事线目前主要走文件导入——stale_vs_storyline 的首批真实触发场景是 goal_planner 自动演进与重导入。不影响机制正确性，但 dogfood 频率低，验收以单测 + 构造场景为主。
- **list/diff/pick/generate 前多一次指纹计算**：切片查询是 3 张小表的索引读，开销可忽略（故事线表行数 ≪ plan 卡）。
- 与 task 245 的 `quality_flag` 同理：新列均为窄加列迁移，旧库幂等补列。

---

## 接受注记

（待 owner 书面拍板：「接受 tech-m4-followup-s5，按 B1–B8 开编码」或点名修改。未接受前不建编码任务。）

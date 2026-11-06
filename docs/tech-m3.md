# M3 技术方案：章内 Variant（抽卡）

- **状态：** 2026-11-06 Asia/Shanghai。只覆盖 [prd-v1.md](prd-v1.md) 的 **M3**（章内 Variant / 抽卡；默认 N=2；`pick` 不改 Canon）。**已接受**（2026-11-06 Asia/Shanghai；owner widget t104s937「接受 tech-m3，按 B1–B7 开 M3 编码」；B1–B7 原样）。包版本仍是 `0.5.0`。
- **本文不做的决定：** 不规划 M4（`chapter continue` / `review`）的实现步骤。不要把本文扩成整代路线图。
- **前置：** M2 步 1–6 与 tech-m2 §6–7 代码验收已在证据 tip `main` `f1c3093` **PASS**（验收文档 #54 @ `1fa7fb0`）。包版本仍是 `0.5.0`。

Owner 要求技术方案按里程碑、小步推进。M3 让作者在同一章号、同一份 Canon 快照下生成 N 个可丢弃草稿槽，diff 后人工 `pick`；`pick` 只移动工作正文指针，**绝不**写入 `plan_*` 的 approved Canon。

---

## 1. 目标

作者对一个已有项目能走完：

- **W1（抽卡段）：** `variant generate --n 2`（默认 N=2）→ 同章两槽草稿 → `variant list` / `diff` → 人 `pick` 一槽 → 工作正文指针指向该槽正文
- **不改 Canon：** `pick` / `generate` / `abandon` 前后，`plan_*` 的 `approved` 行集合不变；不调用 `canon confirm`；不自动入典
- **费用可见：** 报告 / list 暴露 per-slot 费用估计字段（S7 口径字段落地；产品周期数值不挡代码验收）
- **S4 / S5 可观测：** 能记录人选的 slot_index（不全是 1 号时可观测）；pick 后工作正文相对该槽原稿的 diff 可算（人改率代理，不评文学）

不自动选优，不做 Git `branch`，不无人值守连载，不注册 `chapter continue` / `review`，不升包版本，不声称 V1.0 完成。

---

## 2. 仓库里已经有的

M3 在 M0–M2 的 Canon / today / check / content_stale / 承诺之上加章内抽卡；**不重写**这些模块的权威语义，除非本节与 §3–§4 写明的窄改建。

| 能力 | 位置 | M3 怎么用 |
|------|------|-----------|
| 只读工作台 | `cli/commands/workbench.py` 的 `canon show` / `today` | 复用；`today` 可在闭环步提示「可抽卡」类固定文案（不把 variant 写成已入典） |
| Canon 写路径 | `cli/commands/canon_write.py` | **M3 不改**入典 / 销账 / `--hard` 语义。Canon 变更后由 fingerprint 比对标 `stale_vs_canon`（见 B3） |
| 规则检查 | `cli/commands/check.py` | 仍不写库；可选报告某章 variant 的 stale_vs_canon 摘要（只读） |
| 计划事实 / 圣经 | `PlanFactRepository`、`load_chapter_plan_bible` | **generate 只读** approved 快照（属性 source 含 plan\|human\|extract）。pending / rejected **不得**注入（S8） |
| 章头 / 正文 | `ChapterHead`（`current_version_id` / `accepted_version_id` / `status` / `content_stale`）、`ChapterVersion`（只追加） | **工作正文指针** = `ChapterHead.current_version_id`。`pick` 只改该指针（及 variant 行 status）；**不** UPDATE 既有 `chapter_versions.content` |
| 费用遥测 | `llm_call_usage` + `LlmCallUsageRepository`（`cost_cny`、`version_id`） | generate 按 slot 记账；variant 行存汇总估计；list / 报告可读 |
| 生成节点 | `workflows/_nodes.py` 等 Writer 路径 | 可薄复用「写一章草稿」能力，但作者主路径是 `variant *`，不是 `run --auto-confirm` |
| 迁移 | `db/migrations.py` 的 `_MIGRATIONS` | M3 **允许**：新建 `chapter_variants` 表（及必要索引）。不加 Git 分支表；不把 `ChapterHead.status` 改成 PRD §4.2 全文生命周期 |
| 测试布局 | `tests/cli/` 不被默认 pytest 收集 | 新 CLI 测试放这里；圣经 / 计划卡回归仍放原位 |

现码 **没有** `chapter_variants` 表；**没有** `parent_canon_fingerprint` 计算函数；**没有** `variant` 命令组；`ChapterVersion` / `ChapterHead` **不是** Variant 语义（版本是只追加正文历史；Variant 是同章多槽草稿 + pick 指针）。模板加载器里的 `variant` 字样是**题材模板变体目录**，与章内抽卡无关，禁止混用。

这些是本里程碑要接的缺口，不是 M4。

---

## 3. 做、改、不做

### 3.1 做

1. **新建 `chapter_variants` 表**与仓库读写（字段见 B1）。
2. **`parent_canon_fingerprint`：** 对「本章 generate 可见的 approved Canon 快照」做稳定序列化后哈希（B2）；写入每个新生成的 variant 行。
3. **`variant generate`：** 默认 `--n 2`；只读 Canon 快照；为每个 slot 追加一条 `ChapterVersion`（正文）+ 一条 variant 行；**不**自动 pick；按 slot 记费用。
4. **`variant list` / `diff`：** 列出同章槽位；两槽正文可 diff；暴露 status / fingerprint / cost / 可选分数。
5. **`variant pick`：** 同章至多一个 `picked`；只把 `ChapterHead.current_version_id` 指到该槽 `content_ref`；**不**写 `plan_*`；**不**覆盖其它槽正文。
6. **`variant abandon`：** 软删除（status→`abandoned`）；不物理删正文行；不得把已 `picked` 槽的正文内容 UPDATE 掉。
7. **Canon 漂移：** 当前 fingerprint ≠ `parent_canon_fingerprint` → 标 `stale_vs_canon`；仍可读；不得当作默认续写底稿（B3）。
8. CLI / 仓库测试覆盖第 6 节。

### 3.2 改

- 新增 CLI 组 `variant`（仅本里程碑落地的子命令；**禁止**先注册空桩）。
- **窄迁移：** 建 `chapter_variants`（B1）；不改五张 `plan_*` 的 CHECK；不删 `content_stale`。
- `ChapterHead.current_version_id`：在 `pick` 时更新；`accepted_version_id` **本里程碑默认不动**（settled / 人收正式稿属更后语义；若实现需同步，须在步内测试写明且仍不改 Canon）。
- `today` / 帮助文案：闭环步可加「可 `variant generate`」类固定提示；不把抽卡写成已入典。
- 可选：`check` 只读附带本章 variant stale 摘要；仍不写库。

### 3.3 不做

- `chapter continue` / `review` 作为作者主路径（**M4**）。
- 自动 pick / 自动选优 / 「best」分数自动采纳。
- Git 式整树 `branch`；平行设定另开 Project。
- 无人值守多章连载；把 `run --auto-confirm` 写成作者抽卡主路径。
- 注册「打印未实现」的空 `variant` / `continue` 桩。
- 改写 M0–M2 已接受语义（Canon 三态、`content_stale`、promise 销账、extract→pending、S8）。
- 给 `plan_*` 加列；把 SettlementExtractor 权威改回直接入典。
- 改 `pyproject.toml` 版本（保持 `0.5.0`）；声称 V1.0 完成。
- 在本文件里写 M4 实现步骤。第 9 节只列「留给以后」。

### 3.4 绑定决策（具体）

下列决策在**接受本文后**对编码有约束力；实现切片不得静默改写。未接受前本文仅为草稿。

#### B1. 新建 `chapter_variants` 表；正文引用 `chapter_versions`

| 列 | 约束 |
|----|------|
| `variant_id` | TEXT PK |
| `project_id` | TEXT NOT NULL |
| `chapter_number` | INTEGER NOT NULL（≡ PRD `chapter_no`） |
| `slot_index` | INTEGER NOT NULL（1..N） |
| `status` | TEXT NOT NULL；`generated` \| `picked` \| `abandoned` \| `archived` |
| `parent_canon_fingerprint` | TEXT NOT NULL |
| `content_ref` | TEXT NOT NULL → `chapter_versions.version_id` |
| `stale_vs_canon` | INTEGER NOT NULL DEFAULT 0（1=相对当前 Canon 过期） |
| `score_card_json` | TEXT NULL（可选轻分数；不驱动 auto-pick） |
| `cost_cny_estimate` | REAL NOT NULL DEFAULT 0（per-slot 汇总估计） |
| `created_at` / `updated_at` | TEXT NOT NULL |

- **不**把 Variant 塞进 `chapter_heads` 多行，**不**复用 `foreshadowings` / `plan_*`。
- generate 为每槽 **INSERT** 新 `ChapterVersion`（只追加；`version_type` 用既有 `draft` 或实现锁定的等价值），variant.`content_ref` 指向它。
- 同章 `(project_id, chapter_number, slot_index)` 在「未 abandoned/archived」集合内唯一；具体唯一索引实现锁定，测试锁死。
- 同章同时最多一行 `status='picked'`（用事务 + 查询守卫；失败退出码 2）。

短理由：PRD §4.2 明确「表还未建」；正文历史已有只追加版本表，引用比再存一份 blob 更一致。

**备选（拒绝默认）：** 把多槽塞进单一 `ChapterVersion.generation_metadata` JSON。不可审计、难 diff/费用按槽、易覆盖。评审应拒。

#### B2. `parent_canon_fingerprint` = 本章可见 approved Canon 的稳定哈希

- 输入：与 `load_chapter_plan_bible(project_id, chapter_number)` **同一可见集合**的 approved 计划事实（实体 / 属性 / 关系等实现时与圣经加载对齐），按稳定键排序后规范化序列化（建议 canonical JSON），再 `sha256` hex。
- **不含** pending / rejected；**不含**正文；**不含**故事线骨架（故事线不是 Canon）。若日后要纳入故事线，另开修订。
- generate 时计算并写入；list / pick / diff 可读。
- 短理由：与 S8 圣经口径一致，避免「生成时看见的」和「指纹承诺的」两套集合。

**备选：** 指纹含故事线或全库任意表。扩大漂移噪音；默认不做。

#### B3. Canon 变更 → `stale_vs_canon`；仍可读，不作默认续写底稿

- 当「当前指纹」≠ 行上 `parent_canon_fingerprint` 时，将该行 `stale_vs_canon=1`（可在 `list` / `diff` / `pick` / `generate` 前懒标记；也可在 M2 的 hard confirm 成功后对覆盖章批量标记——实现选一种，测试锁死；**不得**为此改写 `content_stale` 语义）。
- `stale_vs_canon` 是**独立旗标**，不挤掉 `generated|picked|…` status（避免丢掉「曾被 pick」信息）。
- `pick` 目标若已 `stale_vs_canon=1`：默认拒绝（退出码 2）；显式 `--allow-stale` 才允许（仍不改 Canon）。
- 新 `generate` **不得** UPDATE 已 `picked` 槽的 `chapter_versions.content`；需要新写法 → 新 slot 或先 abandon 再生成（实现锁定：默认新 slot / 新 version 行）。
- M2 的 `chapter_heads.content_stale`（正文相对硬典过期）与 variant 的 `stale_vs_canon`（草稿相对生成时 Canon 指纹过期）**并存**；文案区分，不合并成一列。

#### B4. `pick` 只移动工作正文指针；永不写 Canon

- 工作正文指针 = `ChapterHead.current_version_id` ← 被 pick 槽的 `content_ref`。
- 同章原 `picked` 行 → `archived`（或 `generated` 保留可读——**锁定为 `archived`**，避免双 picked）；新行 → `picked`。
- **禁止**任何 `plan_*` 的 INSERT/UPDATE（approved/pending/rejected 皆不因 pick/generate/abandon 而变）。测试用前后快照断言。
- **禁止**因 pick 自动 `canon confirm` / 自动标 `content_stale`。

#### B5. `abandon` = 软删除；不覆盖已 pick 正文

- `abandon`：`status='abandoned'`；可选同时 `ChapterVersion.is_abandoned=1`（若与现网 `mark_abandoned` 对齐）；**不** DELETE 行，**不**清空 content。
- 已 `picked` 的槽：`abandon` 默认拒绝（退出码 2），除非先 pick 其它槽或显式旗标（实现锁定；推荐先 pick 其它再 abandon 旧槽）。
- 新 generate **不得**把正文写入已有 `picked` 的 `content_ref` 行（只追加新 version）。

#### B6. 默认 N=2；无 auto-pick；无空桩；费用按槽

- `variant generate` 默认 `--n 2`；允许显式更大 N，但文档与助手日用说明不鼓励 >2；塌缩时先查 diversify / 章拍，不先把默认改成 >2（PRD）。
- generate **结束时所有新槽均为 `generated`**，绝不变 `picked`。
- 不注册 `branch`；不注册未实现的 `variant` 子命令空桩；子命令随 §5 小步落地。
- 预算耗尽：停止后续 slot；已完成 slot 保留；退出码 **3**。
- per-slot：`cost_cny_estimate` + 底层 `llm_call_usage` 用 `version_id=content_ref` 关联；口径可按 PRD S7 估算（¥2/M 入、¥8/M 出）写估计，标注非账单。
- **无**「自动 best / 最高分采纳」。

#### B7. 坐落在 M0–M2 之上，不重写

| 既有 | M3 关系 |
|------|---------|
| `canon show` / `today` | 仍只读 Canon/承诺；today 文案可提示抽卡，不把 variant 当 Canon |
| `canon edit/confirm/dismiss` / promise | 不变；hard confirm 可触发覆盖章 variant 标脏（B3），但不改入典规则 |
| `check` | 仍不写库；可不读 variant 也能过 M2 回归；M3 可加只读摘要 |
| `content_stale` | 章正文相对硬典；与 `stale_vs_canon` 分立 |
| extract→pending / S8 | generate **只读** approved 圣经；pending 零泄漏 |
| 包版本 `0.5.0` | 不 bump |

---

## 4. 接口

### 4.1 命令（增量）

```text
songyan variant generate --project-id TEXT --chapter INT [--n 2] [--budget-cny FLOAT] [--json]
songyan variant list     --project-id TEXT --chapter INT [--json]
songyan variant diff     --project-id TEXT --chapter INT --a INT --b INT [--json]
# --a/--b 为 slot_index
songyan variant pick     --project-id TEXT --chapter INT --slot INT [--allow-stale] [--json]
songyan variant abandon  --project-id TEXT --chapter INT --slot INT [--json]
```

退出码：`0` 成功；`1` 缺库 / 缺项目 / 参数非法；`2` 业务拒绝（双 pick、abandon 被拒、stale 未允许、目标槽不存在等）；`3` 预算耗尽（generate 部分成功时：已写 slot 保留 + 退出 3，测试锁死）。

### 4.2 generate 语义

1. 计算 B2 指纹；只读 `load_chapter_plan_bible` 可见集合。
2. 为 slot_index=1..n 各创建 `ChapterVersion` + `chapter_variants` 行（`status=generated`，`stale_vs_canon=0`）。
3. 不修改任何 `plan_*` 行；不修改其它章；不自动 pick。
4. 调用模型失败：已成功 slot 保留；失败信息进退出码 / stderr；不写半截 content 覆盖旧 picked。
5. 作者路径文档不把 `run --auto-confirm` 当作本命令的别名。

### 4.3 pick / abandon / list / diff 语义

1. `list`：输出各槽 slot / status / stale 旗标 / fingerprint 短显 / cost / content_ref；可选分数。
2. `diff`：两槽正文 unified 或行级 diff（实现锁定）；槽缺失 → 退出 1 或 2（锁死）。
3. `pick`：B4；断言 `plan_*` approved 快照前后一致。
4. `abandon`：B5。

### 4.4 模块边界

| 文件 | 责任 |
|------|------|
| `db/migrations.py` | `chapter_variants` 窄迁移 |
| `db/` 新 repo 或 `repository.py` 扩展 | variant CRUD；同章单 picked 守卫 |
| `services/` 薄封装 | fingerprint；generate 编排；cost 汇总 |
| `cli/commands/variant.py`（新） | 五个子命令 |
| `cli/main.py` / 注册点 | 挂载 `variant` 组（随步落地，无空桩） |
| `models/` | Variant 模型 |
| `tests/cli/test_variant_*.py` | CliRunner；不测文学；生成可 mock 模型 |

### 4.5 本里程碑不做的命令表面

- 不注册 `chapter continue`、`review`、`branch`、独立 `status` 产品命令。
- 不注册「打印未实现」空桩。

---

## 5. 小步

**本文已接受。** 按下列小步写 `tasks/22x` **编码**任务。每步一个可独立拒绝的 PR。不要合成一个大 PR。合并前 Mew COMMENT（不代 owner 点 APPROVE，除非另有授权）。

### 步 1 — 表 + fingerprint + 仓库（无作者 generate 调用）

**产出：** 迁移 `chapter_variants`；fingerprint 纯函数 + 单测；repo 插入/列表/同章单 picked 守卫。可不注册 CLI，或只注册 `variant list` 对空章返回空列表（若注册则必须真能跑，禁止「未实现」桩）。

**测试：** 迁移可重复；指纹对同一 approved 集合稳定；pending 变更不改变指纹；双 picked 写入失败。

### 步 2 — `variant generate`（默认 N=2，mock 模型）

**产出：** generate 写 N 条 version + variant；只读 Canon；不 auto-pick；per-slot cost 字段；预算耗尽 → 退出 3。

**测试：** N=2 两行 `generated`；`plan_*` 前后一致；S8：圣经路径仍 0 泄漏 pending；无 pick。

### 步 3 — `variant list` / `diff`

**产出：** 列表与两槽 diff；json 表面。

**测试：** 同章两稿可 diff；缺槽错误码锁死。

### 步 4 — `variant pick` / `abandon`

**产出：** pick 改 `current_version_id` + status 转换；abandon 软删；不覆盖 picked 正文；`plan_*` 不变。

**测试：** PRD M3 验收：pick 前后 approved 不变；同章仅一 picked；abandon 后仍可读 content；再 generate 不 UPDATE 已 pick 的 version 行。

### 步 5 — `stale_vs_canon` + 费用在报告/list 可见

**产出：** Canon 变更后标脏；pick 默认拒 stale；list/report 有 per-slot 费用；S4 可记录 slot_index（测试夹具可选非 1 号 pick）。

**测试：** 改 approved 属性后旧 variant `stale_vs_canon=1`；`--allow-stale` 才可 pick；费用字段非空（可为 0 的夹具但字段存在）。

### 步 6 — 闭环文案与文档同步

**产出：** today `next` 如需提示抽卡则更新固定文案；STATUS / HANDOFF 记步次；**不**写 V1.0 完成；**不** bump `0.5.0`。

每步合并前跑第 7 节命令。`git diff` 不得出现包版本 bump；不得引入 `continue` / `review` / `branch` 注册。

---

## 6. 验收

与 PRD §7.2 M3 条、§4.2 Variant 语义、§9.3，以及 **S4 / S5 / S7** 中可代码化的部分、**S8** 对齐。

**最小验收表面（硬门）：**

| 表面 | 必须 |
|------|------|
| `variant generate --n 2` | 同章两槽 `generated`；只读 Canon；不 auto-pick |
| `variant list` / `diff` | 两稿可 diff |
| `variant pick` | 只改工作正文指针；`plan_*` approved 不变 |
| `variant abandon` | 软删；不删/不清已 pick 正文内容 |
| per-slot 费用字段 | list 或报告可见 |
| stale_vs_canon | Canon 变更后可读标脏；默认不可作 pick/续写底稿 |
| S8 | generate 不注入 pending |

清单：

1. 默认 N=2；generate 后无自动 `picked`。
2. 同章同时至多一个 `picked`。
3. `pick` 前后 `plan_*` approved 行集合不变；无新的 canon confirm 副作用。
4. 新 generate 不 UPDATE 已 `picked` 的 `chapter_versions.content`。
5. `abandon` 后行仍在，status=`abandoned`，正文可读。
6. 修改 approved Canon 后，旧 variant `stale_vs_canon=1`；无 `--allow-stale` 时 pick 失败（退出码 2）。
7. list/报告含 per-slot `cost_cny_estimate`（或等价字段名，测试锁死）。
8. 测试夹具至少一次 `pick --slot 2`（S4 可观测）；或文档化两次皆 slot 1 并注明需查塌缩——**代码验收要求夹具能 pick 非 1 号**。
9. pick 后工作正文与该槽 `content_ref` 一致；人改率（S5）以「pick 后 content 相对生成原稿可 diff」为代理，不设文学阈值门槛。
10. 无 `branch`；无空桩命令；无 `continue` / `review` 注册；`pyproject.toml` 仍为 `0.5.0`。
11. `ruff check src/ tests/` 通过；默认 pytest 与本里程碑 CLI 测试通过；既有计划卡 / 圣经 / M0–M2 CLI 回归通过（文案有意更新须在 PR 说明）。

S4/S5/S7 的产品周期统计不挡代码验收；代码验收以本节命令级清单为准。

---

## 7. 验证命令

```bash
ruff check src/ tests/
python -m pytest tests/db/test_plan_fact_cards.py tests/db/test_dushi_lingyi_plan_facts.py tests/plan_checks/test_plan_bible_runtime.py -q
python -m pytest tests/cli/test_workbench_commands.py tests/cli/test_canon_write_commands.py tests/cli/test_check_command.py -q
# 实现后追加，例如：
# python -m pytest tests/cli/test_variant_generate.py tests/cli/test_variant_list_diff.py tests/cli/test_variant_pick_abandon.py -q
# 含迁移 / fingerprint 则加跑对应 DB 测试
```

不必为了 M3 代码验收去跑真实 LLM 长窗；generate 测试用 mock / 夹具即可。真实模型冒烟另开维护者任务，不挡 §6 硬门。

---

## 8. 风险

| 风险 | 处理 |
|------|------|
| 用 JSON 塞多槽进单 version 行 | B1：独立表 + content_ref；评审拒绝挤兑方案 |
| pick 误写入 Canon / 触发 confirm | B4 + 前后快照测试 |
| generate 覆盖已 pick 正文 | B5：只追加；禁止 UPDATE 该 content_ref |
| 空桩 `variant` 出现在帮助里 | 禁止；子命令随步注册 |
| 指纹含 pending / 故事线导致乱飘 | B2：仅 approved Canon，与圣经对齐 |
| 与 `content_stale` 概念混淆 | B3：分立旗标与文案 |
| 自动选优 / 默认 N>2 | B6：禁止 auto-pick；默认 N=2 |
| 范围膨胀到 continue / review / 无人值守 | 停；改 PRD 并另审 |
| 包版本或 V1.0 完成话术 | 禁止 |
| 模板目录名 `variant` 与抽卡术语混淆 | 文档与标识使用 `chapter_variants` / `variant` 命令组；不碰模板加载器语义 |

都市灵异只作夹具题材标签。命令里不出现「若题材是都市灵异则……」分支。

---

## 9. 以后的技术方案

本文若被接受并完成 M3 之后，才轮到：

- `chapter continue` / `review`（**M4**）
- continue 默认是否可 `--variants 2` 转入本表
- 人几乎不改就标 settled 的警告（S5 产品向）
- 是否把故事线纳入 fingerprint（仅当 B2 不够用）

那些属于 M4 或后续修订各自的 `docs/tech-m*.md`。本文不写其实现步骤。

---

## 接受注记

**已接受**（2026-11-06 Asia/Shanghai）。依据 owner widget **t104s937**：「接受 tech-m3，按 B1–B7 开 M3 编码」。**B1–B7 原样接受**，无点名修改项。

接受后按 §5 小步推进。步 1 已在 `main`（#56 / `b9bbf98`）。**当前切片 = 步 2**（`variant generate`；owner t104s953）。包仍 `0.5.0`；不声称 V1.0 完成。

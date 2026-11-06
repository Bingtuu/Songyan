# M2 技术方案：硬事实标脏、承诺债务与抽取提案

- **状态：** 2026-11-04 Asia/Shanghai。只覆盖 [prd-v1.md](prd-v1.md) 的 **M2**（W4 改典涟漪、W5 承诺债务、SettlementExtractor / import 抽取进提案）。**已接受。** 步 1–6 已进 `main`；§6–7 代码验收 **PASS**（`main` `f1c3093`，2026-11-06）。接受注记见文末。包版本仍是 `0.5.0`。
- **本文不做的决定：** 不规划 M3–M4（`variant *`、`chapter continue` / `review`）。不要把本文扩成整代路线图。
- **前置：** M1 步 1–5 与 tech-m1 §6–7 代码验收已在 `main` `69d7ece` **PASS**（验收文档 #42 @ `5a6e45b`）。包版本仍是 `0.5.0`。

Owner 要求技术方案按里程碑、小步推进。M2 让作者在改硬典后看见过期章、看见并人工销掉伏笔债，并把结算 / 导入抽取变成提案而不是 Canon。

---

## 1. 目标

作者对一个已有项目能走完：

- **W4：** 人在 `canon confirm` 时标明硬变更 → 覆盖章被标 `content_stale`（不改正文、不重抽）→ `check` 报告受影响范围
- **W5：** `today` 计数 `foreshadowings` 的 `planted` / `due` / `overdue`；`canon show --kind promise` 列出开放承诺；人给出章号与证据经 confirm 销账
- **抽取提案：** SettlementExtractor / import 抽取结果进入提案队列（`plan_*` 的 `pending`）→ 既有 `canon triage` / `confirm` / `dismiss` → 入典后才进 `list_canon_*`；S8 仍 0 泄漏

不调用模型写终稿，不自动重写脏章，不注册 `variant` / `chapter continue` / `review`，不升包版本，不声称 V1.0 完成。

---

## 2. 仓库里已经有的

M2 在 M1 写路径与只读工作台之上加标脏、承诺阅读 / 销账、抽取→提案；不重写这些模块的权威语义，除非本节与 §3–§4 写明的改建。

| 能力 | 位置 | M2 怎么用 |
|------|------|-----------|
| 只读工作台 | `cli/commands/workbench.py` 的 `canon show` / `today` | 扩展：`today` 增加承诺计数；`canon show --kind promise` 读 `foreshadowings` |
| Canon 写路径 | `cli/commands/canon_write.py` 的 `edit` / `confirm` / `dismiss` / 非持久 `accept` | 复用三态；`confirm` 增加 `--hard` / `--mark-stale`；新增 promise 销账子命令（仍挂在 `canon` 下，**不**新开 `promise` 组） |
| 规则检查 | `cli/commands/check.py` + `run_plan_fact_gate` | 仍不写库；报告增加 stale / 受影响范围说明 |
| 计划事实 | `PlanFactRepository`、`models/plan_facts.py` | 提案行仍走 `pending`→`approved`/`rejected`。属性 `source` 现仅 `plan`\|`human`（见 §4.4） |
| 本章圣经 | `load_chapter_plan_bible` | **只读锁定**：只读 `approved`。pending / rejected / 未确认抽取 **不得**出现（S8） |
| 章头 / 正文 | `ChapterHead`（`status`: `draft`\|`under_review`\|`accepted`）、`ChapterVersion`（只追加） | 标脏**不**改 `ChapterVersion.content`；不覆盖旧版本行 |
| 伏笔 | 表 `foreshadowings`；`ForeshadowingRepository`（`list_active` / `list_schedulable` / `update_status`）；列 `resolved_chapter` / `resolved_version_id` 已存在 | W5 与 S3 **只用这张表**。不建第二张伏笔表，不另起 plant/open/paid 枚举 |
| 结算 | `SettlementExtractor`、`apply_settlement`（写角色 / 设定 / 伏笔 / 数值等结算库） | 助手路径改为提案入 `plan_*` pending；旧结算表保留为 `untrusted_until_confirmed` 只读对照，**不**升格第二真源 |
| 导入 | `import` 组（`ingest`…`replay` / `synthesize` / `publish`） | 已有；M2 增加：导入抽取样例行 confirm 前不进 `list_canon_*` |
| 迁移 | `db/migrations.py` 的 `_MIGRATIONS` | M2 允许：**窄**迁移（`chapter_heads.content_stale`；`plan_attributes.source` CHECK 扩 `extract`）。**不加** `hardness` 列，不建 variant 表 |
| 测试布局 | `tests/cli/` 不被默认 pytest 收集 | 新 CLI 测试放这里；圣经 / 计划卡 / 伏笔回归仍放原位 |

现码 **没有** `hardness` 列；`ChapterHead` **没有** stale 字段；`today` **尚未**计伏笔；`canon show` **尚未**支持 `--kind promise`；`PlanFactSource` **仅** `plan`\|`human`；`apply_settlement` **仍**直接写结算库。这些是本里程碑要接的缺口，不是 M3/M4。

---

## 3. 做、改、不做

### 3.1 做

1. **W4 硬变更涟漪：** `canon confirm`（至少 attribute；entity 若带显式章范围亦可）支持 `--hard`：按覆盖章号将对应 `chapter_heads.content_stale=1`。软注记默认不标脏；软注记若要标脏必须显式 `--mark-stale`。
2. **范围算法：** 以 `valid_from_ch` / `valid_to_ch`（闭区间）为主；证据里的章号可并入。两端皆空且无证据章号 → **不猜成脏**。不算到的章不标。
3. **`check`：** 报告受影响 / 已标 stale 的章范围；仍不写库、不入典、不调用写作节点。
4. **W5 承诺阅读：** `today` 列出 `planted` / `due` / `overdue` 条数（及可读的年龄摘要）；`canon show --kind promise` 列出开放条目。不把开放伏笔写成已确认 Canon 事实。
5. **W5 人确认销账：** 人提供章号与证据，经 `canon confirm` 的 promise 表面写入 `status=resolved` 且回填 `resolved_chapter` / `resolved_version_id`。未经 confirm 不得把该条从作者路径的 open 集合抹掉。
6. **抽取→提案：** SettlementExtractor / import 抽取映射为 `plan_*` 的 `pending` 行；`confirm` / `dismiss` 复用 M1。新事实在 confirm 前不在 `list_canon_*`；S8 守住圣经。
7. **旧结算表：** 保留；作者 / 对照读径可标 `untrusted_until_confirmed`；默认不 approve。
8. CLI / 仓库测试覆盖第 6 节。

### 3.2 改

- 扩展 `workbench`：`today` 载荷与文案；`canon show` 增加 `--kind promise`（及既有 kind 过滤若尚未落地则一并最小接通 promise）。
- 扩展 `canon confirm`：计划行增加 `--hard` / `--mark-stale`；新增 promise 销账参数（章号 + 证据）。
- **窄迁移：** `chapter_heads` 增加 `content_stale INTEGER NOT NULL DEFAULT 0`（可选 `stale_marked_at TEXT`）；**不**把 `status` 枚举改写成 PRD §4.2 全文生命周期（那是跨里程碑语义，M2 只加标脏位）。
- **窄迁移（属性 source）：** `plan_attributes.source` CHECK 从 `('plan','human')` 扩到含 `'extract'`；同步 `PlanFactSource`、`plan_fact_repo._SOURCE`、`list_canon_attributes`（approved 且 `source IN ('plan','human','extract')`）。
- 助手路径上：抽取结果**先**写 `pending` 提案；模型声称的伏笔 `resolved` **只算提案**，人 confirm 后才清 open 集。
- `apply_settlement`：**不得**把新事实写成 plan Canon；对作者路径承诺销账不得在无 human confirm 时清 open 集。结算库其它观测写入可保留供对照，但文档与读径打标 `untrusted_until_confirmed`。具体切入点按 §5 小步拆，避免一步翻全引擎。

### 3.3 不做

- `variant *` / Variant 表 / `parent_canon_fingerprint`（**M3**）。
- `chapter continue` / `review` 作为作者主路径（**M4**）。
- 自动重写脏章、自动重抽、自动调用写作节点。
- 给五张 `plan_*` 表加 `hardness` 列（本里程碑用命令旗标，见 §3.4）。
- 第二张伏笔表；`promise` 独立命令组；plant/open/paid 新枚举。
- 持久第四态 `accepted`（M1 已禁，M2 不恢复）。
- 改 `pyproject.toml` 版本（保持 `0.5.0`）；声称 V1.0 完成。
- 题材专用检查器；注册空桩 `variant` / `continue`。
- 在本文件里写 M3+ 实现步骤。第 9 节只列「留给以后」。

### 3.4 绑定决策（具体）

下列决策在**接受本文后**对编码有约束力；实现切片不得静默改写。

#### B1. 「硬」= 命令旗标，不加 `hardness` 列

| 情况 | 行为 |
|------|------|
| `canon confirm …` **无**旗标 | 入典；**不**标脏（软注记默认） |
| `canon confirm … --hard` | 入典 + 按 §3.1 范围标 `content_stale=1` |
| 软注记但人要标脏 | `canon confirm … --mark-stale`（显式）；不必先有 hardness 列 |
| `--hard` 与 `--mark-stale` 同时 | 允许；效果都是标脏，范围算法相同 |

短理由：现码无 hardness；M1 刚做过五表 CHECK 重建。旗标满足 PRD「技术方案再定旗标还是列」，且最小 schema、TDD 友好。若日后要按事实查询软硬，再开修订加列，不在 M2 首轮。

#### B2. 脏标记落在 `chapter_heads.content_stale`，不改写正文

- 新列：`content_stale INTEGER NOT NULL DEFAULT 0`（1=过期标记）。
- **不**把 `ChapterHead.status` 从 `draft|under_review|accepted` 改成 PRD 目标态机全文；M2 只回答「这章正文是否相对硬典过期」。
- 标脏 **不** UPDATE `chapter_versions.content`；若人另存修订，仍是新版本行（只追加）。
- 清除 stale：人显式动作（实现时可挂在 confirm 成功后的后续命令或 `canon` 子旗标）；**不得**因标脏自动清。首轮验收以「能标上 + check 能看见」为硬门；清除可以同里程碑后步，但不得做成自动重写。

#### B3. 承诺队列复用 `foreshadowings` + 既有 confirm 语义

- Open 集（作者路径）：`status IN ('planted','due','overdue')` 且实现时与 `lifecycle_status` 的既有产品口径对齐（优先可读的 active 债；S3 统计口径写进测试夹具说明）。
- `today`：计数至少含 planted / due / overdue；不得把这些行渲染成「已入典事实」。
- `canon show --kind promise`：列表；只读。
- 销账：`canon confirm promise`（名称实现可微调，但必须挂在 `canon` 下）要求 `--chapter` + 证据；写入 `resolved` + `resolved_chapter` + `resolved_version_id`。
- **不**新开 `songyan promise …` 命令组。
- 模型 / 结算声称 resolved：作者路径上 **只进提案**（pending 销账建议或等价）；**不得**在无 human confirm 时把该条移出 open 集（PRD §6.6 验收 2）。

#### B4. 提案队列 = `plan_*` 的 `pending` / `approved` / `rejected`

- 不新建第二套 proposal 表。
- 抽取映射为计划行：`approval_status=pending`；属性 `source='extract'`（B5）。
- 入典 / 驳回：复用 `confirm` / `dismiss`（及非持久 `accept` 规则不变）。
- `list_canon_*` / 圣经：确认前不可见（S8）。

#### B5. `PlanFactSource` 增加 `extract`

- `Literal["plan","human","extract"]`；`plan_attributes` CHECK 同步。
- `list_canon_attributes`：`approved` 且 `source IN ('plan','human','extract')`。
- 人写路径仍强制 `source=human`（M1 不变）。
- 短理由：比把抽取伪装成 `plan`/`human` 更可审计；只动属性 source 一列 CHECK，避免五表大迁移。

#### B6. 结算库保留为不信任对照

- 旧结算表不删。
- 作者主路径 Canon = 已 confirm 的 `plan_*`。
- 读结算对照时文档 / CLI 可标注 `untrusted_until_confirmed`；默认不 approve。

---

## 4. 接口

### 4.1 命令（增量）

```text
# W4：在既有 confirm 上增加旗标（entity / attribute；验收硬门见 §6）
songyan canon confirm attribute --project-id TEXT --attribute-id TEXT [--hard|--mark-stale]
songyan canon confirm entity    --project-id TEXT --entity-id TEXT [--hard|--mark-stale]
# 若 entity 无 valid 窗口：--hard 须带显式章范围旗标（实现名锁定，如 --from-ch/--to-ch），否则不标脏

# W5
songyan today --project-id TEXT [--json]          # 增加 promise 计数
songyan canon show --project-id TEXT [--kind promise] [--json]
songyan canon confirm promise --project-id TEXT --foreshadowing-id TEXT --chapter INT --evidence TEXT
# evidence：人给的短证据串；resolved_version_id 实现时可从该章 accepted_version_id 解析，缺则退出码 1/2（实现锁定）

# 提案仍走
songyan canon confirm|dismiss …   # 对 pending extract 行
songyan check --project-id TEXT --chapter INT [--json]   # 报告含 stale 范围
```

退出码沿用 PRD §9.3 / M1：`0` 成功；`1` 缺库 / 缺项目 / 参数非法；`2` 用于 check 无章可查或硬伤，以及「要标脏但范围不可算」类可恢复的业务拒绝（实现与测试锁死，避免与 1 混用）。`3` M2 不使用（无预算路径）。

### 4.2 W4 写入语义

1. confirm 入典语义与 M1 相同（`approved`；无持久 `accepted`）。
2. 仅当 `--hard` 或 `--mark-stale` 时计算章集合并写 `content_stale=1`。
3. 章集合为空或不完整可算 → 不标脏；输出写明原因；入典是否同时成功：`confirm` 的入典与标脏宜同事务——若旗标要求标脏但范围不可算，**整命令失败**（不入典也不标脏），避免「已入典却漏标」。软确认无旗标则只入典。
4. 禁止自动调用 Writer / 修订节点；禁止 UPDATE 既有 `chapter_versions` 正文。

### 4.3 W5 写入语义

1. 阅读路径只读 `foreshadowings`。
2. 人销账是唯一清 open 集的作者路径写动作（就承诺状态而言）。
3. 结算模型产出的 resolve 建议 → pending；dismiss 可驳回；confirm 才 `resolved` + 追溯列。

### 4.4 提案 / source 语义

1. 抽取器或 import 映射写入 `pending`；属性 `source=extract`。
2. confirm → `approved`（source 保持 `extract`，进入 `list_canon_attributes`）。
3. dismiss → `rejected`；默认 Pending 段不可见（M1 规则）。
4. `apply_settlement` 不得直接 `approval_status=approved` 写 `plan_*`。

### 4.5 模块边界

| 文件 | 责任 |
|------|------|
| `cli/commands/workbench.py` | today 计数；canon show promise |
| `cli/commands/canon_write.py` | `--hard` / `--mark-stale`；promise confirm |
| `cli/commands/check.py` | 报告 stale 范围 |
| `db/repository.py`（ChapterHead） / 迁移 | `content_stale` 读写 |
| `db/settlement_repo.py` / 服务薄封装 | 人销账写 `resolved_*`；open 列表 |
| `models/plan_facts.py` + `plan_fact_repo.py` | `extract` source；canon 过滤 |
| `agents/settlement_extractor/` 与 import 衔接 | 提案入队；作者路径 resolve≠清债 |
| `tests/cli/test_*` | CliRunner；不测文学；不调真实模型 |

### 4.6 本里程碑不做的命令表面

- 不注册 `variant`、`chapter continue`、`review`、独立 `promise` 组、独立 `status` 产品命令。
- 不注册「打印未实现」空桩。

---

## 5. 小步

**本文已接受。** 按下列小步写 `tasks/21x` **编码**任务。每步一个可独立拒绝的 PR。不要合成一个大 PR。合并前 Mew COMMENT（不代 owner 点 APPROVE，除非另有授权）。

### 步 1 — W5 只读：today 承诺计数 + `canon show --kind promise`

**产出：** 从 `foreshadowings` 读 planted/due/overdue 计数与列表；不写库；不把承诺写成 Canon 事实。

**测试：** 插入 overdue 夹具后 today 计数含它；`--kind promise` 可见；S8 无关路径不泄漏 pending plan 行。

### 步 2 — W5 人确认销账

**产出：** `canon confirm promise`（章号+证据）→ `resolved` + `resolved_chapter` / `resolved_version_id`；无 confirm 则仍在 open 集。

**测试：** PRD §6.6 验收 1–3；模型/提案未确认不得清 open 集。

### 步 3 — W4：`content_stale` 迁移 + confirm `--hard` / `--mark-stale`

**产出：** 窄迁移；硬确认按 `valid_from_ch`/`valid_to_ch` 标脏；软默认不标；不可算范围则整命令失败（§4.2）。

**测试：** 覆盖 2–4 章的硬属性变更 → 2/3/4 stale，1 与 5 不 stale；`chapter_versions` 旧行未被覆盖；无写作节点调用。

### 步 4 — `check` 报告 stale 范围

**产出：** check 输出含受影响 / stale 章信息；仍不写库。

**测试：** 标脏后 check 点名范围；检查前后 plan 行与 `content_stale` 之外无意外写入（check 本身不改 stale）。

### 步 5 — 抽取 / import → pending 提案（`source=extract`）+ S8

**产出：** source CHECK 扩 `extract`；抽取入队 pending；confirm 前不在 `list_canon_*`；confirm 后可见；结算库保留且不升格 Canon。

**测试：** PRD §7.3 / 导入 M2 条；S8 0 泄漏；`apply_settlement` 不直接 approve plan 行。

### 步 6 — 闭环文案与文档同步

**产出：** today `next` 如需提示承诺债 / 硬确认则更新固定文案；STATUS / HANDOFF 记步次；**不**写 V1.0 完成；**不** bump `0.5.0`。

每步合并前跑第 7 节命令。`git diff` 不得出现包版本 bump；不得引入 variant 表或 continue 命令。

---

## 6. 验收

与 PRD §6.5–6.6、§7.3、导入 M2 条及 **S8** 对齐。

**最小验收表面（硬门）：**

| 表面 | 必须 |
|------|------|
| `today` 承诺计数 | planted/due/overdue 可读 |
| `canon show --kind promise` | 开放条目列表 |
| `canon confirm promise` | 人销账 + 追溯列 |
| `canon confirm attribute --hard` | 窗口内章 `content_stale` |
| `check` | 报告 stale / 影响范围且不写库 |
| 抽取→pending→confirm | confirm 前不在 `list_canon_*`；S8 |

清单：

1. 覆盖第 2–4 章的硬属性变更后，第 2、3、4 章 `content_stale=1`，第 1、5 章为 0。
2. 正文版本表既有行不被覆盖；无自动写作节点。
3. 软确认无旗标 → 不标脏；`--mark-stale` 可显式标脏。
4. 插入 `overdue` 后 `today` 计数含它，且不写成已确认 Canon 事实。
5. 未经 confirm 的销账不把该条移出 open 集；confirm 后写 `resolved_*`。
6. S3 统计基于现表 `foreshadowings`，无第二伏笔表。
7. 一次结算 / 导入抽取后，新事实不在 `list_canon_*` 直到 confirm；圣经 S8 = 0 泄漏。
8. 旧结算表仍在；对照读径可标 `untrusted_until_confirmed`。
9. 无 `hardness` 列；无 variant / continue 注册；`pyproject.toml` 仍为 `0.5.0`。
10. `ruff check src/ tests/` 通过；默认 pytest 与本里程碑 CLI 测试通过；既有计划卡 / 圣经 / M0–M1 CLI 回归通过（文案有意更新须在 PR 说明）。

S3 的产品周期数值不挡代码验收；代码验收以本节命令级清单为准。

---

## 7. 验证命令

```bash
ruff check src/ tests/
python -m pytest tests/db/test_plan_fact_cards.py tests/db/test_dushi_lingyi_plan_facts.py tests/plan_checks/test_plan_bible_runtime.py -q
python -m pytest tests/cli/test_workbench_commands.py tests/cli/test_canon_write_commands.py tests/cli/test_check_command.py -q
# 实现后追加本里程碑 CLI / DB 测试文件名，原则：CLI 单独跑；含迁移则加跑相关 DB 测试
```

不必为了 M2 去跑真实 LLM 长窗。

---

## 8. 风险

| 风险 | 处理 |
|------|------|
| 软注记误标整章脏 | 默认不标；要标必须 `--hard` 或 `--mark-stale` |
| 不可算章号却乱标 | 不算则不标；与入典同事务失败（§4.2） |
| 把 `ChapterHead.status` 整表改成 PRD 态机 | 禁止；只加 `content_stale` |
| 新建 promise 命令组 / 第二伏笔表 | 评审拒绝 |
| 抽取直接 approve 进 Canon | 强制 pending；S8 测试 |
| 把结算库当第二真源 | 文档与读径 `untrusted_until_confirmed` |
| 模型 resolve 直接清债 | B3：作者路径必须 human confirm |
| 五表加 hardness 大迁移 | B1：本里程碑用旗标 |
| 范围膨胀到 variant / continue / 自动改写 | 停；改 PRD 并另审 |
| 包版本或 V1.0 完成话术 | 禁止 |

都市灵异只作夹具题材标签。命令里不出现「若题材是都市灵异则……」分支。

---

## 9. 以后的技术方案

本文已接受。完成 M2 之后，才轮到：

- Variant 表与 `variant *`（M3）
- `chapter continue` / `review`（M4）
- 是否补 `hardness` 列或章生命周期全文枚举（仅当旗标不够用）
- 生产路径从正文观察属性（超出 M1 夹具注入）的加厚
- rejected / extract 提案的审计列表 UX

那些属于 M3、M4 或后续修订各自的 `docs/tech-m*.md`。

---

## 接受注记

**已接受** 2026-11-04 Asia/Shanghai；依据 owner widget t93s804「接受 tech-m2，按 B1–B6 开 M2 编码」；B1–B6 原样接受；下一刀 = M2 步 1。

**合入本文档 PR 之后的下一刀：** M2 **步 1** 编码（W5 只读：today 承诺计数 + `canon show --kind promise`），TDD；开 PR 后 **Mew COMMENT** 再合并（勿在无 COMMENT 时自合）。本接受注记不授权在本文档 PR 内改 `src/` 行为。

# tech-roadmap-post-m4 · M4/§9 全清零后的下一步（路线调研与技术方案 v1）

| 项 | 内容 |
|---|---|
| 状态 | 草稿（task 254，2026-11-13）——**路线级方案：方向待 owner 拍板；拍板前不建编码任务** |
| 关联 | PRD §5 / :473 / :559 / §5.2；tech-m4 §9 与 tech-m4-followup(-s5) 全部闭环（2026-11-13）；STATUS/HANDOFF |
| 范围 | 四个候选方向的内容、切片、成本与推荐排序；方向确认后各方向单独走「任务文档 → 技术方案 → 拍板 → 编码」 |

---

## 1. 现状盘点：已闭环与余留面

**已闭环（2026-11-08 至 11-13）：** M0–M4 代码验收全量 PASS；tech-m4 §9 四项（真实冒烟与导入续写验收 / `chapter status` / `review --deep` / S5 产品向）全部交付；245/246 两个 P1 修复进 main；§9/S5 清零。

**PRD 余留面（取证）：**

| # | 余留 | PRD 依据 | 性质 |
|---|---|---|---|
| R1 | 故事线无编辑写径：只能 `outline_import` 文件导入，不能命令行增改删查 | :17「人设计并决定……故事线」、:48「维护事实和故事线」、P-bench「人编辑事实**与**故事线」；249 冒烟实证 | 产品缺口（P-bench 核心面） |
| R2 | S1–S7 信号无汇总面：通过口径已定，但 `today`/`report` 无聚合输出；S5 趋势需落表 | §5.2「怎么算通过」 | 度量缺口 |
| R3 | 「review 可以警告，**并且可以关掉**」——253 的 accept 人改率警告无关闭开关 | :473 | 小缺口（PRD 字面） |
| R4 | `project new \| list \| init` 别名 `[proposed]` 未做 | :559 | 小项 |
| R5 | 两个既有测试 flake（doctor 子进程 / canon promise 并发），干净树可复现 | — | 质量债 |
| R6 | S6（today 打开天数 ≥3/周）与 S9（文学人工抽读） | §5.2 | owner 侧维护者任务，非编码 |

**约束自检（AGENTS.md）：** 四方向均不碰题材检查器 / 自动选优 / 「可发表」声称；R1 属「人编辑」写径（与 canon edit 同形），R2 是只读度量，R3/R5 是修补。

## 2. 方向候选

### 方向 A · 故事线编辑 CLI（R1）

**依据**：P-bench 是产品两条腿之一，「人编辑事实与故事线」目前只闭环了一半（事实有 `canon edit/confirm`，故事线只能整文件导入——改一个弧目标要重导整个 outline 文件，249 冒烟已实证此摩擦）。

**内容**（与 `canon` 命令族同形，全部人写径、提案或直写需拍板）：
- `storyline show --project-id [--json]`：outline + arcs + threads 分开展示（M0 已有展示面，补 --json/编辑前置对齐）
- `storyline edit outline --project-id [--core-conflict ...] [--mainline-synopsis ...] [--themes ...] [--intended-ending ...]`：upsert 全书大纲行
- `storyline edit arc --project-id --arc-id [--arc-goal ...] [--start ...] [--end ...] [--open-thread ...] [--resolve-thread ...]`：增改弧（边界移动自动联动 252 的 stale_vs_storyline）
- `storyline edit thread --project-id --thread-id [--title ...] [--description ...] [--status ...] [--opened-chapter ...] [--expected-resolve-arc ...]`
- `storyline remove arc/thread`：软删或硬删需拍板（threads 被 arcs 引用时的 FK 口径）

**关键决策**：故事线是「规划」不是 Canon——直写还是先进提案队列（pending）？推荐**直写但留审计**（storyline 无 approved/pending 三态语义，硬套 plan 卡三态是过度设计；`genre_runtime_profile_history` 有历史表先例可仿），B 点拍板。

**成本**：2–3 个编码切片 + tests/cli。**风险**：低（表结构与 repo 现成，纯 CLI 写径组装）。**验收**：CRUD 全测 + 改动后 252 标脏联动 + 全量回归。

### 方向 B · S 信号度量面（R2）

**依据**：§5.2 每个信号都写了「怎么算通过」，但产品没有输出这些信号的地方——信号无法被看 = 无法被用。S5 已算（253）但无趋势；S1–S3、S7 有数据源无聚合。

**内容**：
- `today` 或 `report` 加 `signals` 分区（推荐 `report`，today 保持「一句下一步」的薄）：S1 周确认数+dismiss 比、S2 冲突关闭周期、S3 开放伏笔年龄 P50、S4 抽卡采纳分布（pick 的 slot 号分布）、S5 人改率分布（需落表：chapter_heads 加 edit_ratio 列，accept 时写入）、S7 单章成本预算完成率
- S5 落表是唯一的写面新增（窄列迁移，accept 写入点已现成）

**成本**：2 个编码切片（S5 落表 + signals 聚合渲染）。**风险**：低-中（聚合口径要按 §5.2 逐字对齐，防「指标编造」）。**验收**：每个信号的口径单测（拿 §5.2 当断言表）+ 手造数据验证。

### 方向 C · 质量打磨小项（R3/R4/R5）

**内容**：① `chapter accept` 加 `--no-edit-warn`（或配置开关，B 点定形态）满足 :473「可以关掉」；② `project list`（:559 的 proposed 别名里最实用的一个；new/init 别名可顺手）；③ 两个 flake 修复（doctor 子进程测试在本机的环境问题实证、canon promise 并发测试的时序加固）。

**成本**：1–2 个小切片。**风险**：低。**验收**：flake 双跑稳定 + 开关测试 + 全量绿。

### 方向 D · Dogfood 优先（R6）

**内容**：owner 用 W2 在真实模型上写 3–5 章（沿用 249 runbook 模式），产出复盘：真实使用摩擦清单（命令面 / 文案 / 流程断点）→ 逐项转新立项。助手侧只备 runbook 与记录模板。

**成本**：owner 时间为主，¥2–3 模型费；助手编码为零或随暴露缺口而定。**风险**：无（不代码）。**价值**：最高信号质量——连续三轮冒烟修出的 245/246 都是 dogfood 型发现。

## 3. 推荐排序与理由

| 排序 | 方向 | 理由 |
|---|---|---|
| 1 | **D 先行或并行**（维护者任务，不占编码队列） | 三轮冒烟证明真实使用是最高价值的发现源；R1/R2 的「该做多厚」只有 dogfood 能校准 |
| 2 | **A 故事线编辑 CLI** | PRD 明文缺口 + P-bench 核心面；没有它，「人编辑故事线」要靠重导文件，252 的标脏联动也缺少触发源 |
| 3 | **C 质量小项**（顺手清账） | 小而确定；:473 是 PRD 字面承诺；flake 影响每次回归的可信度 |
| 4 | **B S 信号度量面** | 有价值但可等一轮 dogfood——信号聚合的厚薄（尤其 S5 趋势/S4 分布）取决于真实使用节奏，先建可能空转 |

**依赖关系**：A/C 彼此独立且与 D 并行；B 的 S5 落表与 A 无冲突。若 dogfood 先行，A 可缩到「最小编辑面」（edit arc goal + thread status 两个最痛命令），余量按复盘加。

## 4. B 决策点（路线拍板用）

| # | 决策点 | 推荐 | 备选 |
|---|---|---|---|
| B1 | 方向组合与顺序 | D 并行 + A → C → B（B 等 dogfood 校准） | A+B 直接全做；只做 A+C |
| B2 | 故事线写径形态 | 直写 + 历史审计表（仿 genre_runtime_profile_history） | 先进提案队列（重 plan 三态，不推荐） |
| B3 | storyline remove 语义 | 软删（status=archived） | 硬删（需解引用检查） |
| B4 | 警告开关形态 | `--no-edit-warn` 命令旗标（最简） | 项目级配置列 |
| B5 | S5 落表位置 | chapter_heads.edit_ratio 窄列（accept 写入） | 独立信号表（YAGNI） |
| B6 | signals 输出位置 | `report` 加分区（today 保持薄） | today 加（会胖） |
| B7 | 本轮是否动 :559 别名 | 只做 `project list` | 全做（new/init 别名） |
| B8 | 不做清单 | 题材检查器 / 自动选优 / 「可发表」声称 / 把 S9 文学做成自动门 / 多项目并发工作台 | —（红线照 AGENTS.md） |

## 5. 任务拆分草案（方向拍板后各独立项）

| 任务 | 内容 | 依赖 |
|---|---|---|
| 255+ | 方向 A：storyline 编辑 CLI（按 B2/B3 定稿） | B1/B2/B3 |
| 258+ | 方向 C：--no-edit-warn + project list + flake 修复 | B4/B7 |
| 260+ | 方向 B：S5 落表 + report signals 分区 | B5/B6（建议等 D 复盘） |
| D | owner 侧 dogfood：助手备 runbook，暴露缺口另行立项 | B1 |

---

## 接受注记

（待 owner 书面拍板：确认方向组合与 B1–B7 口径，或点名修改。路线确认后各方向按仓库惯例单独走技术方案。）

# Songyan 质量门方法论：CED / T9 / 五门

> 面向外部技术用户。本文档定义 Songyan 的三个质量度量口径：统计什么、不统计什么、证据要求、阈值与出处、以及如何在自己的 run 上复现计算。
> 阅读本文不需要任何历史任务文档。文中所有复现命令均在真实 run 上实际执行过，示例输出经过脱敏（不含正文、路径、密钥）。

---

## 总览

| 口径 | 度量对象 | 一句话定义 | 门禁语义 |
|------|----------|-----------|----------|
| CED | 审查报告中的一致性错误 | 每千字正文中「带正文证据的一致性错误」数量 | 五门之一，相对 sci-fi baseline 判定 |
| T9 | accepted 正文的文本洁净度 | 元标记泄漏 / 整段重复 / 时间线矛盾三类计数 | 元标记与整段重复为硬红线（必须为 0） |
| 五门 | 项目级验收 | budget / CED / overdue / health / completeness 五项 PASS/FAIL | 用于体裁 Ch100 爬坡验收 |

共同前提：

- **SQLite 是唯一长期事实源**。三个口径的输入全部来自 SQLite 中的 accepted 章节、审查报告和派生度量表，不依赖内存状态或日志文本。
- **统计对象是 accepted 章节**。未通过的草稿、被回滚的版本不进入统计。
- **证据驱动**。没有正文证据（`evidence_quote`）的审查意见不进入 CED 统计；没有定位信息的检测结果不进入 T9 统计。

---

## CED（Consistency Error Density，一致性错误密度）

### 定义

```text
CED = 一致性证据 issue 数 / accepted 正文总字数 × 1000
```

字数口径：中文字符（CJK 统一表意文字）按字计数，连续的字母数字串按一个 token 计数。实现见 `src/songyan/evals/five_gate_acceptance.py` 的 `word_count()`。

### 统计范围

只统计以下 7 个类别的一致性 issue（实现：`src/songyan/evals/consistency_ced.py` 的 `CONSISTENCY_CATEGORIES`）：

| 类别 | 含义 |
|------|------|
| `world_consistency` | 世界观/设定一致性 |
| `character_behavior` | 角色行为一致性 |
| `dialogue_distinctness` | 对话区分度 |
| `supporting_character_goal_presence` | 配角目标在场性 |
| `continuity` | 连续性 |
| `state_mismatch` | 状态不匹配 |
| `setting_conflict` | 设定冲突 |

不在此清单内的类别（如文学工艺类观察）**不进入** CED。

### 证据要求

计入 CED 的 issue 必须同时满足：

1. `severity` 为 `critical` 或 `major`；
2. 携带非空 `evidence_quote`（正文原文引句）。

`minor` 级别或无证据引句的 issue 不计入。

### 排除项与防双计数

- **`rule-mr-*` 排除**：RuleAuditor 的 mandatory-reference 聚合 issue（`issue_id` 以 `rule-mr-` 开头）不计入。其 `evidence_quote` 存放的是缺失设定 key 而非正文句，计入会虚增 CED。
- **merged 优先**：同一版本存在 ReviewMerger 合并报告（`audit_type = "merged"`）时只统计 merged 报告；不存在时回退到 source auditor 报告。同一 issue 不会被 source 与 merged 双计数。
- **审查版本回退**：accepted 版本自身无审查报告时（例如 accept 发生在修订后），回退到其 parent 版本的审查报告取值。

### 出处

- 证据口径（critical/major + evidence_quote）：内部 Task 172a.7 定义。
- 7 类别清单、merged 优先、`rule-mr-*` 排除：内部 Task 172b.q 冻结，helper 实现提交 `1f25ed8`，收口修正提交 `9c4226e`。

---

## T9（文本洁净度）

### 定义

T9 对 accepted 正文逐章统计三类计数（实现：`src/songyan/evals/text_cleanliness.py`）：

| 指标 | 检测内容 | 检测器来源 |
|------|----------|-----------|
| 元标记泄漏 | 正文中的 meta 标记、markdown 场景标题、文本 artifact（如斜杠拼接痕迹），三者合并计数 | `rule_auditor` 的 meta tag / scene title / artifact 检测器 |
| 重复长段落 | 章内或跨章的整段重复 | `rule_auditor` 的重复段落检测器 |
| 时间线矛盾 | 跨章时间信号冲突 | `timeline_consistency` 的时间信号提取与冲突检测 |

### 红线语义

- **元标记泄漏 = 0、重复长段落 = 0 是硬红线**。PASS 样本必须在 clean rerun 后达到 T9=0，不接受解释性豁免。
- **时间线矛盾默认 report-only**：计入展示，不进入硬红线（由 `t9_include_timeline_in_redline` 开关控制，默认 `False`）。

判定实现：`src/songyan/evals/v6_acceptance.py` 的 `check_t9()`，走 `persist=False` 纯内存路径，不写库。

### 出处

- 指标实现：内部 Task 164（V7），提交 `1fc290e`。
- 硬红线冻结：内部 Task 165（V7）阈值校准，「元标记泄漏数=0、整段落重复章数=0 为硬红线；跨章时间线矛盾默认 report-only」。

---

## 五门验收（Five-Gate Acceptance）

五门是体裁爬坡（如 Ch100）的项目级验收判定，实现于 `src/songyan/evals/five_gate_acceptance.py`（`evaluate_metrics()`）。

| 门 | 判定 | 阈值 |
|----|------|------|
| budget | `budget_used_peak < 1.0` 且无 halt | 上下文预算峰值不得触顶，且无质量熔断 |
| CED | `目标 CED ≤ sci-fi baseline × 1.15` | 容差系数 `CED_TOLERANCE = 1.15` |
| overdue | 目标逾期未收伏笔数 ≤ sci-fi 同章尺度 | 与 baseline 同章比较，不设绝对值 |
| health | 最新 continuity health ≥ 8.0 | 且健康报告的覆盖章号不得超过评估边界（防 stale health） |
| completeness | accepted 缺口 `gap ≤ 1` | `accepted ≥ up_to - 1` |

### baseline 与插值

- 正式 baseline 为包内资源 `src/songyan/evals/baselines/scifi_ch100_baseline.json`（`baseline_id = scifi_ch100_v8_freeze`），含 Ch25 / 50 / 75 / 100 四个点，随包分发。
- 非 baseline 点的章号按相邻两点线性插值；低于 Ch25 的评估直接使用 Ch25 点。
- baseline 同时保留 corrected（consistency-only）与 legacy（宽口径）两份 CED 数值，供审计对照；正式判定只用 corrected 值。
- sci-fi baseline 是**相对比较基准**：其他体裁的五门判定均为「不显著差于 sci-fi 同章尺度」，不是绝对分数线。

### halt 语义

budget 门包含 halt 检测：评估边界内存在质量熔断证据（adaptive halt 决策、或 project run 以 `auto_halt*` 原因暂停、或 run 失败）则该门 FAIL。人工暂停、成本暂停等 `pause_reason` 非 `auto_halt` 前缀的记录不计为质量熔断；无 `pause_reason` 字段的历史数据按保守旧行为计为 halt。

### final 语义

`up_to ≥ 100` 时判定为 `final`；低于 100 的判定标注为 early-warning read，仅作预警，不构成正式验收。

### 出处

- 五门原型：内部 Task 172b（V8）体裁爬坡判据。
- 正式化：内部 Task 182，提交 `0feb4e4`，原则为「I/O 可重构，判定函数零漂移」；baseline JSON 同提交引入。

---

## 阈值出处汇总

| 阈值/口径 | 数值 | 冻结出处 | 公开可验证证据 |
|-----------|------|----------|----------------|
| CED 证据要求 | critical/major + evidence_quote | Task 172a.7 | 提交 `1f25ed8`（helper 实现） |
| CED 类别清单 | 7 类 | Task 172b.q | 提交 `1f25ed8`、`9c4226e` |
| CED 容差 | ×1.15 | Task 172b 量化，Task 182 固化 | 提交 `28b0b01`（首次出现）、`0feb4e4`（代码常量） |
| budget 门 | < 1.0 | Task 172b | 提交 `0feb4e4` |
| overdue 门 | ≤ sci-fi 同章尺度 | Task 172b | 提交 `0feb4e4` |
| health 门 | ≥ 8.0 | Task 172b | 提交 `0feb4e4` |
| completeness 门 | gap ≤ 1 | Task 182 | 提交 `0feb4e4` |
| final 边界 | up_to ≥ 100 | Task 182 | 提交 `0feb4e4` |
| T9 硬红线 | meta=0、dup=0 | Task 165（V7） | 提交 `1fc290e`（harness 实现） |
| sci-fi baseline | Ch25/50/75/100 四点 | Task 182 | 提交 `0feb4e4`，包内 JSON |

说明：任务编号（Task 172b.q 等）为内部迭代记录，不随公开仓库分发；提交哈希可在本仓库 git 历史中直接验证。

---

## 复现命令链

以下命令均在真实 run 上实际执行过（执行日期 2026-09-06）。示例输出已脱敏：`myproject` 为占位 project_id，数值为真实执行结果。

### 五门 + CED

```bash
python scripts/five_gate_check.py \
  --genre mygenre \
  --db path/to/songyan.db \
  --project-id myproject \
  --up-to 3 \
  --format text
```

实际输出（一个 3 章启动校准项目，对 Ch25 baseline 点取值）：

```text
=== five-gate check @ Ch3 (mygenre accepted=3) ===
  budget_peak : mygenre 0.982 vs scifi 0.989 -> FAIL
  CED/1k      : mygenre 0.0000 vs scifi 0.3309 (tol x1.15) -> PASS
               consistency-only, merged/source; issues target=0 scifi=32
  overdue     : mygenre 0 vs scifi 61 -> PASS
  health      : mygenre 10.0 (report @Ch3) -> PASS (need >=8.0)
  completeness: accepted 3/3 (gap 0) -> PASS
  --- gate verdict: FAIL (final=False) ---
  NOTE: partial climb; verdict is an early-warning read.
```

退出码：`0` = PASS，`1` = FAIL，`2` = 工具错误（如 DB 不存在）。`--format json` 输出完整结构化结果，其中 `metrics.ced` 段（`issue_count` / `word_count` / `ced_per_1k_words`）即 CED 的独立取数来源。

上例 budget 门 FAIL 的原因是 halt 检测命中：该项目 DB 中存在评估边界内的历史失败 run 记录（`pause_reason` 为空，按保守语义计为 halt）。这演示了 halt 语义的保守性，也说明了为什么五门的正式用途是体裁爬坡验收（`final=True` 需 `up_to ≥ 100`），而非 3 章启动窗口。

注意：

- 该工具以只读模式（SQLite `mode=ro` URI）打开 DB，不写任何表。
- 该脚本位于 `scripts/`，**不随 pip 包分发**，需要克隆仓库执行。打包为 CLI 子命令是 Task 229 的范围。
- `--db` 接受 SQLite 文件路径。你的项目 DB 位置由 `DATABASE_URL` 决定（`.env.example` 默认 `sqlite:///songyan.db`）。

### T9

```bash
songyan metrics --project-id myproject --chapters 1-3
```

输出报告的「文本洁净度（T9 harness 数据源）」段，实际输出（同上 3 章项目）：

```text
- 汇总：元标记 1（含 artifact），重复长段落 0，时间线矛盾 0。

| 章 | 元标记/artifact | 重复长段落 | 时间线矛盾 |
|----|----------------|------------|------------|
| 1  | 0              | 0          | 0          |
| 2  | 0              | 0          | 0          |
| 3  | 1              | 0          | 0          |
```

报告末尾的 V6 验收判据段含 T9 三态行（pass/fail + 三类计数 + 红线口径）。

注意：

- `songyan metrics` 会**重算并持久化派生度量**（写 `text_cleanliness_metrics`、`adaptive_gate_signal_snapshots` 等派生表；不改章节、正文或 settlement 事实）。若需要严格只读的 T9 单口径命令，属 Task 229 范围，交付后本文档将更新。
- 逐章明细（`details_json`，含 artifact 的原文定位）保存在 DB 派生表中，用于内部排查；按脱敏边界不进入公开文档。

---

## 口径不变更纪律

- 本文档定义的口径、阈值、证据要求为**冻结状态**。任何调整（类别增删、阈值改动、证据要求变化）必须另立任务并附回归证据，不允许顺手微调。
- 内部研究性 / report-only 信号不进入本文档口径，也不进入 runtime prompt 或 hard gate。
- 历史口径校准（如 Task 189、192an、193r/193u、193w 对五门取值与 stale health 的修正）只修实现缺陷，不动冻结阈值。

## 已知限制

- **两个阈值的原始取值理由不可考**：completeness 的 `gap ≤ 1` 继承自未入库的 V8 原型脚本；health 的 `8.0` 相对 V7 旧口径 `8.5` 的下调理由未留记录。两处数值自 Task 182 起冻结，口径不再追溯取值理由，调整须另立任务。
- 五门脚本当前需克隆仓库执行，不随 pip 包分发（Task 229 收口）。
- `songyan metrics` 不是只读命令（见上节注意项）。
- sci-fi baseline 覆盖 Ch25-100；低于 Ch25 的评估直接取 Ch25 点，高于 Ch100 的评估取 Ch100 点，均为近似。
- run bundle（`songyan bundle-run`）当前不内嵌三口径的实测数值（占位 `external_not_embedded`），复现必须基于原始 SQLite DB。

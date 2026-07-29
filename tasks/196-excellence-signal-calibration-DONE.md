# Task 196 DONE: 优秀度样本集与校准协议

> **阶段**: V10.3 优秀度信号包（首任务，2026-07-29 用户决策提前启动；wuxia/urban Ch200 爬坡暂停等待 196 结论）
> **类型**: 样本基础设施 / 标注协议 / 离线试点（零侵入生成链路）
> **状态**: ✅ 已完成
> **完成时间**: 2026-07-29

---

## 产物清单

| 产物 | 路径 | 内容 |
|------|------|------|
| 抽样核心模块 | `src/songyan/evals/excellence_sampling.py` | 双库 accepted 正文分层抽样，固定 seed 可复现；读取复用 export_service accepted head 路径，不新建 DB 写路径 |
| 测试 | `tests/evals/test_196_excellence_sampling.py` | seed 复现 / 8 弧段分层覆盖 / 标注 schema 校验 / 错误库拒绝（临时 sqlite fixture） |
| 薄 CLI ×3 | `scripts/build_196_sample_set.py`、`scripts/run_196_prelabel.py`、`scripts/run_196_rule_pilot.py` | 抽样落盘 / LLM 批量预标（纯离线，不接工作流）/ 规则试点 |
| judge 工艺卡 | `src/songyan/prompts/cards/excellence_prelabel/1.0.0.yaml`（含 `_manifest.yaml` 注册） | 四维 1-5 Likert 评分维度定义 + JSON 输出约束 |
| 样本清单 | `tasks/196-excellence-sample-set.json` | 60 章（双库各 30），seed=196，segment_size=25，8 弧段全覆盖 |
| 标注记录 | `tasks/196-excellence-annotations.json` | 72 条 AnnotationRecord：anchor 12 + prelabel 48 + spotcheck 12 |
| 校准报告 | `tasks/196-excellence-calibration-report.md` | 信号边界、report-only vs 候选 gate 划分、试点误报负结果、provenance 声明、对 197-202 接口约定 |

---

## 关键事实

### 样本集

- seed=196 固定可复现；xuanhuan 冻结库（`.tmp/task_v10_xuanhuan_ch200.db`，project `d160a55a…`）与 sci-fi 冻结库（`.tmp/task171_ch1_ch200.db`，project `835afdf1…`）各 30 章，按 25 章弧段分 8 段、每段 3-4 章全覆盖。
- sci-fi 冻结库在库 220 章 accepted（Task 171w Ch201-Ch220 延续），抽样按 `up_to=200` 过滤取 Ch1-200，口径同 Task 189 冻结 baseline。

### 标注三层（72 条）

- **anchor 12 章**：好坏两极各 6（双体裁各 3 强 3 弱），agent 逐章精读，rationale 必含正文证据引用；evidence_quotes 45/45 逐字命中正文（100%）。
- **prelabel 48 章**：LLM 按 judge 卡 `excellence_prelabel/1.0.0` 批量预标，纯离线；evidence_quotes 逐字命中率 94/134 = 70.1%。
- **spotcheck 12 章**：agent 深读复核预标，分歧写入 `disagreement`；evidence_quotes 48/48 逐字命中（100%）。
- provenance 三值按任务书要求逐条真实记录（24 条 `agent-deep-read` + 48 条 `llm-prelabel`）；人工抽审零分歧，未新增 `human-review` 行，未冒充人工真值。

### judge 宽松偏差（校准报告 §5.2）

预标 48 章 × 4 维 = 192 个维度分数：

- 分数 ≤2 的维度数 **0/192**；预标分布整体压扁在 3-5 分，而锚点证明真实分布延伸到 1-2 分（6 个锚点 overall=2）——judge 看不见低分区。
- spotcheck 对照同章预标：**10/12 章**存在 ≥1 个维度分差 ≥2；24 次 ≥2 分歧**全部为 prelabel 偏高**，全部 48 项维度分差无一次 spotcheck 高于 prelabel——单向宽松，无反向。
- 偏差最大维度为 ai_tone（9/12 章差 ≥2 分）：judge 只捕捉文风型 AI 腔，对工程事故型 AI 痕迹（逐字复读、章节号自指泄漏、未渲染标记、设定补丁段）不敏感。
- evidence 保真：prelabel 70.1% vs 锚点/抽检 100%。

### 规则试点负结果（校准报告 §4）

- `detect_ai_tells` + `detect_fatigue_words` 跑全样本 60 章：ai_tells 命中仅 **7/60 章**（0:53 / 1:6 / 2:1），fatigue 词表 mean=0.67、55% 为 0。
- 区分度为零且方向反转：6 个最弱锚点（overall=2）ai_tell 均值 0.00，6 个最强锚点均值 0.33——漏报率 100%，仅有的锚点命中落在最强章上。
- 结论：**现有规则集形态不适合做优秀度校准基准**。不匹配分析（§4.3）证明人工深读缺陷主类是生成/拼装事故类（逐字复读、自指泄漏、工程残留、设定补丁段、模板修辞），完全不在现有文风修辞类模式集内——已作为 Task 198 规则包扩充输入。

### 用户抽审闭环

- 2026-07-29 用户抽审 4 条锚点标注（xuanhuan Ch1 强 / Ch50 弱、scifi Ch104 强 / Ch84 弱），结论：**认可，零分歧**。协议维持"agent 精读锚点 + 人工抽审"路径，未触发降级。

---

## 失败路由触发情况

| 路由 | 触发 | 处理 |
|------|------|------|
| 试点误报率过高无法形成口径 | ✅ 触发 | 按任务书路由**如实记录负结论**：校准报告 §4 降级为负结果（"该规则集现形态不适合做校准基准"），未编造口径 |
| 冻结库 accepted 口径偏差 | ✅ 触发（轻微） | sci-fi 冻结库在库 220 章 accepted vs Ch1-200 口径；经 `up_to=200` 过滤解决，与 Task 189 baseline 同源一致 |
| LLM 预标 JSON 解析失败率 >10% | 未触发 | — |
| 用户抽审发现锚点系统性偏离 | 未触发 | 抽审零分歧，协议未降级 |
| 需要改动运行时代码才能完成抽样 | 未触发 | 抽样复用 export_service 既有读取路径 |

---

## 验收标准逐条对照

- [x] `tasks/196-excellence-sample-set.json` 落盘：双库各 30 章、seed=196 可复现、8 弧段全覆盖。
- [x] `tasks/196-excellence-annotations.json` 落盘：60 章 72 条全量标注，三层 provenance 完整，锚点/抽检含正文证据引用（逐字命中 100%）。
- [x] `tasks/196-excellence-calibration-report.md` 落盘：信号边界（§2）、report-only vs 候选 gate 划分（§3）、试点真实误报负结果（§4）、provenance 声明（§5）、对 197-202 接口约定（§6）。
- [x] 用户抽审完成（2026-07-29，4 章锚点，零分歧认可），分歧记录闭环，未触发降级路由。
- [x] 测试通过、ruff 通过、未违反守护项（见下"验证证据"与"守护项自查"）。
- [x] DONE 文档生成，STATUS/INDEX/V10-README/AGENTS 同步，提交一次不 push。

## 守护项自查

- 未改 Writer / CreativeDirector / 任何 gate / 工作流节点；无新增核心 Agent。
- CED / 五门 / segment audit / T9 口径零改动；`GenreRuntimeProfile` 未动。
- 全部信号离线 report/observe，预标结果不作为任何自动 accept/reject 依据；优秀度、同质化、AI 腔未混入 CED。
- LLM 成本：约 48 次预标调用（每章 1 次，~2K token 量级），走 `.env` 现有配置，未接工作流。
- 未恢复 wuxia / urban Ch200 爬坡。

## 验证证据

| 验证 | 结果 |
|------|------|
| `tests/evals/test_196_excellence_sampling.py` | 全部通过（seed 复现 / 分层覆盖 / schema 校验 / 错误库拒绝） |
| 全量 `python -m pytest tests/ -q`（wrapper `run_with_timeout.ps1 -TimeoutSec 2400`） | **3062 passed, 2 skipped, 1 xfailed**（494.6s，EXIT_CODE=0） |
| `ruff check src/ tests/` | **All checks passed** |
| `git diff --check` | clean |

## commit 清单（79bb622..a6a14b0，15 个）

```
2257dd1 add task 196 excellence sampling core module
8bb1029 cover task 196 db loading with sqlite fixture tests
639b0cf add task 196 sample set builder and frozen 60-chapter sample set
ad72dca harden task 196 sample set builder error handling
2d552bd add task 196 anchor annotations (agent deep-read, 12 chapters)
6626c2a fix task 196 xuanhuan anchor rationale counts
f74bc1a fix task 196 scifi anchor rationale precision
05efbb0 add task 196 excellence prelabel prompt card
cea1563 add task 196 llm prelabel script and 48-chapter prelabel results
493eb6a harden task 196 prelabel script retry and write safety
e5f1c92 add task 196 spotcheck annotations (12 chapters, 10/12 judge disagreement)
fcb0c73 trim task 196 scifi spotcheck rationales to spec length
7e23961 add task 196 rule signal pilot script
c2f264c add task 196 calibration report with pilot false-positive log
a6a14b0 fix task 196 calibration report minor counts
```

（本 DONE 与入口同步为收口提交，未计入上表。）

---

## 后续路由

- **Task 198 规则包扩充输入**：校准报告 §4.3 五类人工深读缺陷（逐字复读 / 自指泄漏 / 工程残留 / 设定补丁段 / 模板修辞），优先做"章内/跨章逐字复读检测"与"自指泄漏/工程残留词面规则"。
- **Task 201 judge 偏差对策输入**：judge 卡 v2 候选（校准报告 §5.3）——① rubric 注入本批 12 锚点好坏两极示例；② 强制检查项覆盖工程事故型缺陷五类；③ 引用必须逐字，非逐字降权或拒绝。偏差建模数据用 spotcheck 的 `disagreement` 字段 + §5.2 单向宽松统计。
- **197/198/200 校准真值**：用 anchor + spotcheck 24 章 agent 深读；prelabel 仅作对照基线，不得当标注真值；消费 prelabel evidence_quotes 前必须逐字校验（70.1% 保真）。

# Task 196: 优秀度样本集与校准协议

> **阶段**: V10.3 优秀度信号包
> **类型**: 样本基础设施 / 标注协议 / 离线试点
> **优先级**: P1
> **依赖**: Task 189（sci-fi Ch200 冻结库与 baseline）；Task 192（xuanhuan Ch200 冻结库）；用户决策：C 组提前启动，wuxia/urban 爬坡暂停等待 196 结论
> **状态**: ◻ 新建（设计已批准）
> **预计工作量**: 中

---

## Goal

为 V10 C 组优秀度信号包建立公共基础：从 xuanhuan + sci-fi 双冻结库分层抽取可复现样本集，定义信号边界与三层标注协议（agent 精读锚点 + LLM 预标 + 人工抽审），并用现成规则检测器完成一次端到端试点，产出第一份真实误报记录与校准口径。

## Context

V10-README 原把 C 组（196-203）整体排在 Ch200 爬坡之后。2026-07-29 用户决策：先做 Task 196 立基，wuxia（Ch125 暂停点）与 urban 爬坡不动，196 完成后再定后续顺序。

196 是 C 组其余全部任务的公共依赖：197/198/200 的信号实现需要样本集与标注真值做校准，201 的 judge 偏差对策需要标注 provenance 记录，203 的报告整合需要信号边界划分。196 不实现任何新信号，只建协议、样本与第一份误报实证。

两条不可违背约束（V10 守护项 + C5）：

- 优秀度信号只做离线 report/observe，不得注入 Writer/CreativeDirector prompt，不得进入自动硬门。
- 优秀度、文学 craft、同质化、AI 腔不得混入 CED；五门判定口径零改动。

**标注协议调整（2026-07-29 用户批准）**：锚点与抽检标注由 agent 逐章精读完成（含理由与正文证据引用），用户以审阅者身份抽查 4-6 章锚点标注（约 20-30 分钟），分歧记入 `disagreement` 字段。标注 provenance 三值：`agent-deep-read` / `llm-prelabel` / `human-review`。校准报告必须明示"锚点真值为 agent 精读 + 人工抽审，非全人工标注"，供 Task 201 设计对照。若用户抽审发现 agent 锚点标注系统性偏离，协议降级回全人工锚点路径。

---

## In Scope（必须完成）

- [ ] 新增抽样核心逻辑 `src/songyan/evals/excellence_sampling.py`：双库 accepted 正文分层抽样，固定 seed 可复现；取正文复用 `export_service.collect_accepted_chapters()` 或 `five_gate_acceptance.py:310` 的 accepted head JOIN 模式，不新建 DB 写路径。
- [ ] 薄 CLI 封装三个脚本：
  - `scripts/build_196_sample_set.py` — 抽样 + 样本清单落盘；
  - `scripts/run_196_prelabel.py` — LLM 批量预标（纯离线，litellm 现有配置）；
  - `scripts/run_196_rule_pilot.py` — 规则信号试点（`detect_ai_tells` + `detect_fatigue_words`）+ 命中对照输出。
- [ ] 预标 judge prompt 工艺卡 `src/songyan/prompts/cards/excellence_prelabel/1.0.0.yaml`（含 `_manifest.yaml` 注册）。
- [ ] 样本清单落盘 `tasks/196-excellence-sample-set.json`：双库各 30 章（每 25 章弧段抽 3-4 章，8 段共 30），含 chapter、version_id、sample_layer、抽样 seed。
- [ ] 标注记录 `tasks/196-excellence-annotations.json`：60 章全量标注（schema 见下），agent 精读锚点 12 章（好坏两极各 6）+ LLM 预标 48 章 + agent 深读抽检 12 章复核预标。
- [ ] 端到端试点：规则信号跑全样本，对照锚点/抽检标注，产出误报记录。
- [ ] 校准报告 `tasks/196-excellence-calibration-report.md`：信号边界（197/198/200 维度对齐）、report-only vs 候选 gate 划分、误报记录、标注 provenance 声明、对 197-202 的接口约定。
- [ ] 产出 `tasks/196-excellence-signal-calibration-DONE.md`，同步 docs/STATUS.md、docs/INDEX.md、tasks/V10-README.md、AGENTS.md 当前阶段行。

## Out of Scope（明确不做）

- 不实现 197 同质化/张力指数、198 AI 腔规则包扩充、199 style card、200 声纹锚点、201 judge 对策、202 perplexity——196 只给它们定边界与样本。
- 不修改 Writer / CreativeDirector / 任何 gate / 工作流节点；不新增核心 Agent。
- 不动 CED、五门、segment audit、T9 口径；不改 `GenreRuntimeProfile`。
- 不恢复 wuxia / urban Ch200 爬坡。
- 预标结果不作为任何自动 accept/reject 依据。

---

## 数据与路径契约

| 项 | 路径 / 口径 |
|----|-------------|
| xuanhuan 冻结库 | `.tmp/task_v10_xuanhuan_ch200.db`（project_id `d160a55a51de4a2bb82440ebc03ec23a`，Ch200 head `v-5659d486`） |
| sci-fi 冻结库 | `.tmp/task171_ch1_ch200.db`（project_id `835afdf11a294b5eac74a5d8998bd9a2`，Task 189 baseline 同源） |
| 样本清单 | `tasks/196-excellence-sample-set.json`（版本管理，对齐 189 baseline 先例） |
| 标注记录 | `tasks/196-excellence-annotations.json`（版本管理） |
| 校准报告 | `tasks/196-excellence-calibration-report.md`（版本管理） |
| LLM 预标原始输出 | `.tmp/196_prelabel_raw/`（不版本管理） |
| 抽样 seed | 固定整数，写入样本清单，保证可复现 |

## 标注 schema

每章一条记录：

```json
{
  "genre": "xuanhuan",
  "chapter": 87,
  "version_id": "v-xxxxxxxx",
  "sample_layer": "anchor | prelabel | spotcheck",
  "scores": {"homogeneity": 3, "tension": 4, "ai_tone": 2, "overall": 4},
  "rationale": "自由文本理由，锚点/抽检标注必须含正文证据引用",
  "evidence_quotes": ["..."],
  "annotator": "agent-deep-read | llm-prelabel | human-review",
  "disagreement": null
}
```

- 评分维度：homogeneity（同质化感知）、tension（张力/节奏）、ai_tone（AI 腔）、overall（整体优秀度），1-5 Likert；对齐 197/198/200 需求。
- `spotcheck` 层与对应 `prelabel` 记录共存，分歧写入 `disagreement`。

---

## 执行阶段

### A. 抽样工具与样本清单

1. 实现 `excellence_sampling.py`：按 25 章弧段分层，每段均匀抽取，固定 seed；输出双库各 30 章。
2. `build_196_sample_set.py` 落盘样本清单 v1（无标注）。

### B. 锚点标注（agent 精读）

1. 从样本清单选 12 章锚点（好坏两极各 6，尽量覆盖早/中/晚期与双体裁）。
2. 逐章精读，按 schema 标注，理由必须含正文证据引用。

### C. LLM 预标

1. 写 `excellence_prelabel/1.0.0.yaml` judge 卡（评分维度定义 + 输出 JSON schema）。
2. `run_196_prelabel.py` 跑 48 章非锚点样本，原始输出落 `.tmp/196_prelabel_raw/`，解析后并入标注记录。
3. 预估成本 < ¥1（60 章 × ~2K token）；脚本必须走 `.env` 现有 LLM 配置，不接工作流。

### D. 抽检复核

1. 从预标样本抽 12 章（20%+），agent 深读复核，记 `disagreement`。
2. 用户抽审 4-6 章锚点标注；分歧并入标注记录。

### E. 规则试点与校准报告

1. `run_196_rule_pilot.py`：ai_tells + fatigue_words 跑全样本，输出逐章命中。
2. 对照锚点/抽检标注，分类误报/漏报，落校准报告。
3. 校准报告定稿信号边界与 report-only vs 候选 gate 划分。

### F. 收口

DONE 文档 + STATUS/INDEX/V10-README/AGENTS 同步。

---

## 失败路由

| 失败点 | 处理 |
|--------|------|
| 冻结库 accepted 正文读取失败/缺章 | 停止，核对 baseline 与 192 DONE 的 head 记录；不绕过 export_service 校验 |
| LLM 预标 JSON 解析失败率高（>10%） | 修 judge 卡输出约束重跑，失败章记 `disagreement="prelabel_parse_failed"`，不硬编补丁数据 |
| 用户抽审发现 agent 锚点系统性偏离 | 协议降级回全人工锚点路径，196 延期，记录偏差案例供 Task 201 |
| 试点误报率过高无法形成口径 | 如实记录"该规则集不适合校准基准"结论，校准报告降级为负结果，不编造口径 |
| 需要改动运行时代码才能完成抽样 | 停止并重审设计；196 不批准任何生成链路改动 |

---

## Review 要求

完成前必须自查：

- 样本集是否固定 seed 可复现，双库各 30 章、8 弧段全覆盖；
- 是否零侵入生成链路（无 Writer/CreativeDirector/gate/prompt 注入改动）；
- 标注 provenance 是否逐条真实记录，无冒充人工真值；
- 误报记录是否来自试点真实输出，非纸面模板；
- 预标 LLM 成本是否落盘可查；
- 是否没有为过关修改 CED/五门/T9 任何口径。

## 测试与验证要求

新增 `tests/evals/test_196_excellence_sampling.py`：

- 固定 seed 抽样结果可复现（两次运行同一清单）；
- 分层覆盖：8 个 25 章弧段均有样本，双库各 30 章；
- 标注 schema 校验（Pydantic，缺字段/越界分数拒绝）；
- 错误 DB 路径 / 空库 / 缺 accepted head 拒绝并报错；
- Mock 策略：抽样用临时 sqlite 测试库；LLM 预标不进单元测试（离线脚本手动验证）。

常规验证：

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 2400 -- python -m pytest tests/ -q
ruff check src/ tests/
git diff --check
```

196 不改运行时代码，无需 scifi 短窗口回归；若实施中发现必须改动共享模块（如 export_service），则补 scifi end10 回归。

---

## 验收标准

- [ ] `tasks/196-excellence-sample-set.json` 落盘：双库各 30 章、seed 可复现、弧段全覆盖。
- [ ] `tasks/196-excellence-annotations.json` 落盘：60 章全量标注，三层 provenance 完整，锚点/抽检含证据引用。
- [ ] `tasks/196-excellence-calibration-report.md` 落盘：信号边界、report-only vs 候选 gate 划分、试点真实误报记录、provenance 声明。
- [ ] 用户抽审完成，分歧记录闭环（或触发降级路由并记录）。
- [ ] 测试通过，ruff 通过，未违反守护项。
- [ ] DONE 文档生成，STATUS/INDEX/V10-README/AGENTS 同步，提交一次不 push。

---

## 参考文档

- `tasks/V10-README.md` — C 组判据（C1-C5）与执行纪律
- `tasks/189-scifi-ch200-baseline.json` — sci-fi 冻结库与 baseline
- `tasks/192-xuanhuan-ch200-climb-DONE.md` — xuanhuan Ch200 冻结库事实
- `docs/reports/v7-literary-framework-review.md` — 170 系列杠杆评估与 voice 度量缺陷（200 前置阅读）
- `src/songyan/utils/ai_tells.py`、`src/songyan/utils/fatigue_words.py` — 试点检测器
- `src/songyan/services/export_service.py` — accepted 正文读取路径

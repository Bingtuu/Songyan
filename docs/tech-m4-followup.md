# tech-m4-followup · §9 后续三项技术方案（chapter status / 导入后再续写验收 / review --deep）

| 项 | 内容 |
|---|---|
| 状态 | 草稿（task 247，2026-11-12）——**待 owner 书面接受后才拆编码任务** |
| 关联 | tech-m4 §9「以后的技术方案」；PRD §9.2 命令树与分工句；task 236 前置调研（N1–N7，尤其 N7 验收分列口径）；task 243（M4 §6–7 PASS @ `e5a33bd`） |
| 范围 | 三项一案三步：**步 1 `chapter status` → 步 2 导入后再续写验收 → 步 3 `review --deep`**。owner 已预拍板：一案三步按此顺序；--deep 成本门 = 交互确认 + `--yes` + `--budget-cny`；chapter status 字段面 = 中薄面 |

tech-m4 §9 原文口径（本文不越出）：

- 「真实模型冒烟与『导入后再续写』验收（维护者任务）」
- 「`chapter status`（若做：只读章进度，不承载 ContextEmergency——B10 分工句）」
- 「`review --deep`（显式 LLM 深审，成本前置提示）」

§9 第四项（故事线纳入 fingerprint / settled 警告，S5 产品向）**不在本案**——产品向，需另行立项。

---

## 1. 结论速览

三项都是 **M4 已交付面的增量**，无新写径、无新表（步 2 纯验收甚至可能零代码）：

| 步 | 交付 | 写库 | LLM | 新表 |
|---|---|---|---|---|
| 1 `chapter status` | 章级只读进度面 | 零 | 无 | 无 |
| 2 导入后再续写验收 | runbook + 真实冒烟记录 + 缺口小修 | 沿用既有写径 | 有（复用管线） | 无 |
| 3 `review --deep` | LLM 深审报告（现有 report 同形合并呈现） | 零（归因走 `llm_call_usage`） | 有（显式、成本前置） | 无 |

依赖关系：三步彼此独立（步 3 建立在 M4 步 4 的 review 零件上，不消费步 1 输出）；排序理由 = 步 1 最小先落地、步 2 是维护者验收、步 3 交互与成本门最复杂放最后。

## 2. 现状面（事实清单，证据 = 文件:行号）

### 2.1 status 面

- 现网 `songyan status` = 项目级计数面（`cli/commands/status.py:86-95`）：章进度六态分布 + `pending_confirm` + ContextEmergency 统计。纯只读。
- 章态六态已有可判定子集映射（`models/chapter_progress.py:30-35`：stale / settled / picked / variants_ready / drafting / empty），推导逻辑在 `services/chapter_progress.py` + `models/chapter_progress.py:68-70`（picked > generated > ……优先级）。
- **`chapter status` 不存在**——PRD §9.2 命令树 `chapter list|status|continue` 中只落了 `continue` 与 `accept`（tech-m4 §2.2），`status` 缺。
- head 双指针（`current_version_id` / `accepted_version_id` / `content_stale`）、variant 槽（`chapter_variants`，含 task 245 新列 `quality_flag`）、槽成本（`cost_cny_estimate`）全部现成可查。

### 2.2 review 面

- 现网 `songyan review` = 七源只读并集 + 复读/专名启发式（`cli/commands/review.py`，M4 步 4 / B8 / N5）。**无 LLM、零写库**（不调 `merge_reviews`）。
- findings 结构现成（`services/review_report.py:83-91`：`severity/source/message/evidence/location`），`--deep` 的 LLM 产出可直接复用同一 `ReviewFinding` 形状合并呈现。
- 被审口径已定：审 `head.current_version_id` 工作稿（未 accept 稿），与 `check` 的 accepted 口径显式分叉（`cli/commands/review.py:1-9` 模块 docstring）。
- N3 已决：review 默认纯只读、不写审计表（task 236 §6 Q3）。`--deep` 延续此口径（见 B5）。

### 2.3 import 面

- import 管线现成：`import ingest → segment → confirm → replay`（`cli/commands/import_pipeline.py:43-234`）。
- replay 自动写径：`_accept_with_replay_mark`（`services/import_replay_service.py:498-560`）同一事务 `accept_version` + head 置 accepted + `import_replay_marks` 幂等标记，**无人确认**。
- **N7 口径（task 236，必须原样继承）**：「无自动 **Canon `approved`**」与「import 可自动 **chapter `accepted`**」是两件事——接口层与验收条目各自分列，绝不混写。本文步 2 验收照此分列（B3）。
- 246 已修 db-maintenance 锁表；244 已修 continue 门禁与圣经——步 2 的两块已知绊脚石已清除。

### 2.4 continue 面（步 2 的被验收对象）

- `chapter continue` W2 短环（task 240）：单章管线 + B5 补跑上一章 settlement（只产 `plan_*` pending）+ B7 `--variants` 转调。M4 §6–7 PASS 后有 task 244/245/246 三轮真实模型复验，单稿与抽卡两路均通。
- 对 **imported 项目** 的 continue：代码上无已知特判断点（continue 按章宇宙/heads 判定，import replay 落的是标准 accepted 副本 + head），但**从未真实模型验证过**——这就是步 2 要补的验收。

## 3. 步 1 · `chapter status`（只读章进度面）

### 3.1 命令面

```
songyan chapter status --project-id TEXT --chapter INT [--json]
```

挂在既有 `chapter` 组（`cli/commands/chapter.py`），与 PRD §9.2 命令树对齐。不新增顶层命令。

### 3.2 字段面（中薄面，owner 已预拍板）

| 分区 | 字段 | 来源 |
|---|---|---|
| 章态 | 六态之一（stale/settled/picked/variants_ready/drafting/empty） | 复用 `chapter_progress` 推导 |
| head 指针 | `current_version_id` / `accepted_version_id` / `content_stale` | `chapter_heads` |
| variant 槽列表 | 每槽 `slot_index / status / quality_flag / stale_vs_canon / cost_cny_estimate` | `chapter_variants`（全状态列出，含 abandoned/archived，与 `variant list` 同序） |
| 本章费用 | 槽成本合计 + `llm_call_usage` 按章 SUM 对照 | `chapter_variants.cost_cny_estimate` / `llm_call_usage` |
| 共审概况 | 最近 `review` findings 按严重度计数（不重建全文报告） | `services/review_report.build_chapter_review` 只读路径 |

**不承载 ContextEmergency**（B10 分工句原样遵守：它只挂项目级 `status`）。

### 3.3 行为口径

- 纯只读，零写库（含不触发 `refresh_stale_vs_canon` 懒标定——status 是观察面不是结算面；stale 展示读取当前值并注明 `as_of` 语义）。
- exit 码（B11 同形）：0 = 成功（章宇宙内）；2 = 章不在章宇宙（业务拒绝，报文案）；1 = 缺库 / 缺项目。
- 文本输出按 3.2 分区；`--json` 同形。槽列表为空时显示「无槽」而非报错。

### 3.4 测试与切片

- TDD：章态映射复用既有推导的装配测试（empty/drafting/picked/settled/stale 五种章各一断言）；exit 2 分支；`--json` 字段完整性。
- 单切片可完成（预计 1 个编码切片 + tests/cli 套件）。

## 4. 步 2 · 导入后再续写验收（真实模型冒烟）

### 4.1 交付形态

**主交付是验收记录，不是代码**。runbook 执行 + 结果落 task 完成总结；仅当发现真实断点才做小修（修切另计）。

### 4.2 runbook（`.tmp/` 冒烟目录，隔离库，gitignore 内）

| 阶段 | 动作 | 预期 |
|---|---|---|
| A 造料 | 新项目 `create-project --template urban` → `run --chapters 1 --auto-confirm` 打出 ch1 accepted | 与 244/245 冒烟同前置 |
| B 导出 | `export` 出 ch1 书稿/清单（现网 `export` 命令） | 导出文件可 re-import |
| C 导入 | 第二个项目（或清库后）`import ingest → segment → confirm → replay` | replay exit 0，`import_replay_marks` 有行，ch1 head 置 accepted（**N7 允许**） |
| D 再续写 | imported 项目 `chapter continue`（ch2）→ 校验 B5 补跑 settlement 只产 pending → `canon confirm` 人工确认 → `chapter accept` → `chapter continue`（ch3，可 `--variants 2`） | W2 短环在 imported 项目上全通；**Canon approved 只来自 confirm（N7 分列另一半）** |
| E 体检 | `status` / `chapter status`（步 1 已落地则用它）/ `check --chapter 3` / `today` | 六态正确、gate passed |
| F 费用 | `llm_call_usage` 归因汇总 | 总费用报 owner，预算熔断 ¥5 |

### 4.3 验收标准（N7 分列写法，照 task 236 定稿）

- [ ] import replay 可自动写 **chapter `accepted`**（ch1 head 双指针齐、marks 幂等）。
- [ ] imported 项目上 W2 短环 ≥2 章连走（continue → confirm → accept → continue），exit 码全符合 B11。
- [ ] 全程**零自动 Canon `approved`**：approved 集只在 `canon confirm` 后增长（前后快照对比）。
- [ ] 已知限制核对：若发现 continue 对 imported 项目的断点（如上一章摘要缺失、指纹口径异常），记录并评估是否小修。
- [ ] 费用归因完整，总花费 ≤ ¥5。

### 4.4 风险预案

- 断点若为 P1 级（如 continue 拒跑 imported 章）→ 当场单切修复再复验，不扩大范围。
- 断点若为设计缺口（如 import 项目无 plan 卡导致圣经恒空）→ 记录为发现，回 owner 决策，不在本步私了。

## 5. 步 3 · `review --deep`（显式 LLM 深审，成本前置）

### 5.1 命令面

```
songyan review --project-id TEXT [--chapter INT] --deep [--yes] [--budget-cny FLOAT]
```

- 不带 `--deep`：现网行为一字不动（七源只读并集，零 LLM，零费用）。
- `--deep`：在现有报告基础上**追加** LLM 深审分区（同一 `ReviewFinding` 形状，source 标 `deep`），同一份报告呈现。

### 5.2 成本前置（owner 已预拍板：交互确认 + `--yes`）

1. 执行 LLM 调用前，按被审正文 token 数 + 深审 prompt 模板估算费用（`count_tokens` + `estimate_cost_from_tokens`，现成工具），打印预估（模型 / 输入输出 token / ¥）。
2. **交互确认 y/N**；`--yes` 跳过确认（脚本/CI 用）。
3. **非 TTY（输出被管道）且未给 `--yes`** → 拒绝执行，exit 2 + stderr 提示（防脚本静默烧钱）。
4. `--budget-cny X`：硬上限；预估超限时拒绝执行（exit 2），不超则执行并在超支时中断（保留已产出部分并注明）。

### 5.3 深审输入与检查口径（B6 待定稿）

输入三件套（只读拼装，零写库）：

1. 被审工作稿正文（`head.current_version_id` 内容，与现 review 同口径）；
2. 本章 approved 圣经（`load_chapter_plan_bible`——task 244 D2 后实体/属性型 Canon 有文本）；
3. 上一章 accepted 摘要（`_get_previous_summary`，120 字截断，现成）。

检查四条建议口径（LLM 结构化输出，映射 `ReviewFinding`）：

1. **事实一致性**：正文引用 vs 圣经的实体/属性/时间锚矛盾（hard）；
2. **连续性**：与上一章摘要的状态/道具/位置断裂（hard/warning）；
3. **复读**：LLM 复核启发式命中的段落（补充而非替代现复读检查，warning/info）；
4. **文风视角**：人称/时态/视角漂移（info；措辞红线：只说「建议人复核」，不评「好不好」）。

### 5.4 写库与归因（B5）

- 深审全程**零写库**：不写 `review_reports`（N3 口径延续）， findings 仅进报告输出。
- LLM 调用走 `call_llm` 标准遥测：contextvars 绑 `agent="review.deep"` + project/chapter，`llm_call_usage` 逐行归因（task 226 机制复用，无第二记账）。
- exit 码：0 = 报告输出（含发现问题，B11 同形）；2 = 成本门拒绝（非 TTY 缺 `--yes` / 超预算）；1 = 缺库 / 缺项目 / 参数非法。LLM 调用失败：报错 exit 1，已生成的非 deep 分区报告仍输出（stderr 注明 deep 分区失败）。

### 5.5 测试与切片

- TDD：成本门三分支（交互确认 / --yes 跳过 / 非 TTY 拒绝）+ 超预算拒绝；deep findings 合并进报告分区（mock call_llm）；零写库断言（49 表快照同 244 冒烟口径）；费用归因行（agent=review.deep）。
- 真实模型复验 1 次（与步 2 冒烟合并或单独，¥1 内），验证深审产出真实 findings 且费用与预估同量级。

## 6. B 决策点（逐条拍板，仿 tech-m4 B1–B12 格式）

| # | 决策点 | 推荐口径 | 备选 / 备注 |
|---|---|---|---|
| B1 | 步 1 命令面与字段面 | §3.1/§3.2 中薄面定稿；挂 `chapter` 组 | 顶层 `status --chapter` 会与 B10 分工句抢面，不取 |
| B2 | ContextEmergency 不挂 `chapter status` | 原样遵守 tech-m4 B10 分工句 | 无 |
| B3 | 步 2 验收分列（N7） | 「import 可自动 chapter accepted；Canon approved 只来自 confirm」逐字写进验收 | 无 |
| B4 | 步 3 成本门 | 交互确认 + `--yes` + `--budget-cny`；非 TTY 无 `--yes` → exit 2（owner 已预拍板） | 「只报费用直接跑」弱化提示，不取 |
| B5 | 步 3 零写库 | deep 不写 `review_reports`，归因走 `llm_call_usage`（N3 延续） | 若 owner 要审计落库，需重开 N3 拍板 |
| B6 | 步 3 输入与检查口径 | 输入三件套 + 检查四条（§5.3） | 检查条数可砍（如只做事实一致性一条 MVP） |
| B7 | 顺序与总预算 | 步 1 → 2 → 3；冒烟预算 ¥5（步 2）+ ¥1（步 3 复验）封顶 | 三步彼此独立，顺序可调；--deep 交互最复杂放最后是推荐节奏 |
| B8 | 不做清单 | 自动选优 / `chapter status` 变写操作 / `--deep` 自动改稿或自动 accept / 题材专用深审检查器 / `--deep` 进 `run` 默认管线 | 红线照 AGENTS.md |

## 7. 验收标准（分列三步）

- **步 1**：`chapter status` 五态装配测试全绿；exit 2 分支锁定；`--json` 字段齐；`tests/cli` 套件过；全量回归 + ruff 绿；真实库手测一次（可并入步 2 冒烟 E 阶段）。
- **步 2**：§4.3 五条全过；费用 ≤ ¥5；结果记录进 task 完成总结。
- **步 3**：§5.5 测试全绿 + 真实模型复验 1 次（¥1 内，费用与预估同量级）；不带 `--deep` 的现网 review 行为零变化（既有测试原样通过）。

总闸门：三步全部 PASS 后，STATUS/HANDOFF 同步，§9 剩余项清零（S5 产品向除外，另行立项）。

## 8. 不做

- S5 产品向项（故事线纳入 fingerprint / 人几乎不改就标 settled 的警告）——另行立项。
- 真实模型长窗无人值守（引擎/冒烟边界不变）。
- 任何新 Canon 写径、新状态机、新表。
- `--deep` 的批量模式（`--chapter all` 之类）——YAGNI，作者逐章看。

## 9. 小步任务拆分（接受后）

| 任务 | 内容 | 依赖 |
|---|---|---|
| 248 | 步 1 `chapter status`（TDD 单切片） | 无 |
| 249 | 步 2 导入后再续写验收（runbook + 真实冒烟 + 缺口小修切） | 无（可与 248 并行） |
| 250 | 步 3 `review --deep`（成本门 + 深审 + 复验） | 无（可与 248/249 并行；排序理由见 §1） |

每步走仓库标准循环：任务文档 → TDD → 全量回归 + ruff → 完工同步 STATUS/HANDOFF → 提交。

---

## 接受注记

（待 owner 书面拍板：「接受 tech-m4-followup，按 B1–B8 开编码」或点名修改。未接受前不建编码任务。）

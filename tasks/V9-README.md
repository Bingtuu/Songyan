# V9 Task 总索引

> **阶段**: 生产化地基 + urban 第三体裁 Ch100（双主线聚焦，串行三段时序）
> **定位**: 自用为主、按开源标准打磨——不追求终端用户产品体验，但地基（打包/CI/日志/导出/成本）按可发布标准补齐
> **当前口径**: V8（含 V8.5）已全量闭环。V9 不做优秀度信号包与跨体裁 Ch200（捆绑留 V10），只做两件事：① 补齐生产化地基；② urban 第三体裁 Ch100 爬坡作为地基的实战验收
> **任务编号**: V9 从 Task 173 开始；**扁平编号**——每个可独立执行、独立验收、独立出 DONE 文档的工作项各占一个编号（粒度对标 V6 的 141-159 / V7 的 160-171w）；编号是 trace id，不等同于严格执行顺序；撞墙定点修复按父任务字母后缀登记（如 `187.p`）
> **状态**: 已开工（2026-07-18：173/174 ⚠️ 条件完成；175 阶段 A-C 代码完成、终审通过，阶段 D 实跑验收待 API 预算确认）

本文是 V9 阶段任务文档的事实入口。V8 历史事实入口见 `tasks/V8-README.md`（任务文档与报告在 `archive/v8/`）；更早阶段见 V7/V6/V5-README。

---

## 一句话目标

> **V9 把系统从"验证过的研究原型"变成"自己天天敢用、按开源标准可发布"的系统：先补齐长跑可靠性、交付发布、爬坡工具链三块生产化地基，再用 urban 第三体裁 Ch100 爬坡（五门冻结口径）作为地基的实战验收。**

---

## 背景与设计依据

### V8 留下的起点

- `GenreRuntimeProfile` 全部运行时字段已接线，可插拔；无 Profile 体裁 100% 回退 scifi 旧行为
- xuanhuan + wuxia 双体裁 Ch100 五门 PASS；爬坡方法论与五门冻结口径（`archive/v8/tasks/172b-xuanhuan-ch100-climb.md` §1.1）已定型，harness（`scripts/run_172b_ch100_climb.py`）经双体裁验证可直接复用
- 172j 已解锁 `max_*` 调参路径（调低生效、调高由动态曲线接管）；172k 给出 urban 标定输入（见"关键输入数据"）
- V8 已登记给 V9 的事项：urban Ch100（先补任务书）、跨体裁 Ch200、按体裁深度调参、GateConfig 构建时序重构（V10 或更晚）、max_* 锚定方案、horizon floor 再校准

### 外部调研要点（2026-07-18，五个方向）

- **一致性方向上本系统已在前列**：2026 年商业产品（Sudowrite/NovelAI/Novelcrafter）全部是被动参考式记忆（Story Bible/Lorebook），无结算校验、无审计闭环；学术原型（DOME、MAGNET/ATLAS）有检测无工程闭环。"enforcement vs reference" 是差异化卖点。ConStory-Bench 实测 DeepSeek 系 CED 约为顶尖闭源 4-5 倍，系统侧补足正是本架构的合理性证据
- **"优秀"的度量已扩展**（同质化/多样性指数、judge 偏差对策、叙事张力、中文 AI 腔规则包、style card 管线）——经评审**捆绑留 V10** 与 Ch200 同期
- **无人值守的工业水位**：成本熔断、修订停滞检测、LiteLLM proxy fallback、tracing、结构化输出校验-回灌重试已有成熟共识——V9 取其中成本追踪与熔断，其余按需要后续评估
- **反面清单（V9 不做）**：多 agent 仿真 bottom-up 生成、Temporal 迁移、小说特化微调（先攒数据）

### 内部生产就绪度审计要点（2026-07-18，十项）

- **P0**：① 解释器退出挂死已复现两次（172k），173 已补 LLM client 显式关闭与最外层 force-exit 兜底；② 全仓库无一次 `structlog.configure`，174 已落地应用日志与关联字段；③ 写完 100 章拿不到书稿（无 export 命令，8+ 任务脚本各复制一份 `_export_prose()`）；④ `pip install .` 成 wheel 即坏——`prompts/`、`genres/`、`creative_modes/`、`project_templates/` 等运行资源不是 package data
- **P1**：成本追踪为零（`phase2_graph.py` 躺 `total_cost=0.0 # TODO`）；CLI 三坑（run 不回显 run_id、`--mode-id` 默认不回读项目 mode、README 表漏 `index` 命令）；无 CI 且 `tests/cli/test_cli.py` 4 个既有失败
- **P2**：Profile 调参只有 Python API 无 CLI；五门判定器在 `.tmp/` 待收编；Windows 防卡协议只是文档未工具化

---

## 阶段验收判定

V9 通过 = A 组（地基）+ B 组（爬坡）同时满足，C 组（守护）全程不破。

### A 组 · 生产化地基判据

| # | 判据 | 对应 Task |
|---|------|-----------|
| A1 | `pip install .`（非 `-e`）装出的 wheel 在非仓库 cwd 能直接跑通 `create-project --template scifi` + `run --chapters 1-3` | 178 |
| A2 | `LOG_LEVEL` 生效；应用日志落盘 `logs/app/`，并与既有 `logs/chapter_runs/` 逐章 JSONL 通过 `run_id/chapter/stage/version_id` 关联；单章事故现场可从应用日志 + run log + DB 重建（代码级完成；重建演示挂起至 175 后补跑） | 174 |
| A3 | `songyan export --project-id <id>` 产出按弧/卷组织的纯净书稿（Markdown/txt） | 177 |
| A4 | LLM 调用 token/成本逐条落库；调用上下文能追溯到 run/chapter/agent；`songyan report` 含成本视图（per run/chapter/agent）；run 级成本预算硬上限，耗尽优雅停跑且可 `--resume` | 175 |
| A5 | 解释器退出挂死有代码级兜底（已落地，附 dry probe 归因证据）；连续两次短窗口实跑进程自然退出（挂起至 175 后补跑） | 173 |
| A6 | CI 上线（ruff + mypy + pytest 分层）；`tests/cli` 不再被默认跳过或由 CI 单独覆盖，4 个既有失败修复，全量绿 | 181 |
| A7 | 五门判定器 + 段审计收编为 `scripts/` 正式工具并参数化；五门判定函数口径不改（I/O、路径、参数化可重构），xuanhuan/wuxia 既有 Ch100 DB 重放结果与归档报告一致 | 182 |
| A8 | `songyan profile show/diff/upsert --genre <g>` 可用；标定迭代全程不改代码 | 183 |

### B 组 · urban Ch100 判据（冻结口径沿用 172b §1.1）

| # | 判据 |
|---|------|
| B1 | Ch1-Ch100 全 accepted（gap≤1 走 documented-isolate 复核） |
| B2 | `budget_used` 峰值 < 1.0 且无 `context_emergency_budget_ratio_halt` |
| B3 | consistency CED ≤ sci-fi 同章尺度 × 1.15 |
| B4 | overdue ≤ sci-fi 同章尺度（不套用短窗口 <5） |
| B5 | health ≥ 8.0（latest 非 None） |
| B6 | T9 = 0（含 urban end15 曾见的 timeline_conflict / meta_tag_leak 复查闭环） |

### C 组 · 守护项（不可违背）

- scifi `--end 10` 逐值回归：任何运行时/工具链改动后，无 Profile 体裁旧行为不变
- CED 口径守护：consistency-only、merged/source、正文证据；不计文学 craft，不计 `rule-mr-*` 聚合项
- T9 口径守护：诊断报告可记录非系统性原因，但 PASS 样本必须 clean rerun 后 T9=0，不接受“解释性豁免”替代通过
- 机制修复后诊断 DB 不作终判样本，必须 clean rerun
- 不改五门冻结判定口径本身；五门工具收编时预算/CED/overdue/health/completeness 的判定函数不改，I/O、路径、参数化和报告渲染可以重构，并以双体裁 DB 重放证明无漂移

---

## Task 状态

> 状态口径：`◻ 规划中` / `🔄 进行中` / `✅ 完成`（有 `*-DONE.md`）/ `⚠️ 条件完成` / `⏳ 占位`。所有任务文档开工前补写，完工后归档 `archive/v9/`。

### V9.1 长跑可靠性

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 173 | 解释器退出挂死修复 | ⚠️ 条件完成 | LLM client 显式 registry + `aclose_llm_clients()`；pipeline wrapper 收尾关闭；`SONGYAN_FORCE_EXIT` / `FORCE_EXIT_AFTER_RUN` 最外层兜底；长跑 harness 默认启用 | DONE: `tasks/173-interpreter-exit-hang-fix-DONE.md`；自动化验证 + dry probe 归因证据完成；scifi end10 与两次自然退出实跑验收挂起至 175 后补跑 |
| 174 | 日志体系落地 | ⚠️ 条件完成 | `logging_setup.py`：CLI/harness 入口 configure 一次；`LOG_LEVEL` 修活；console 人类可读 + `logs/app/*.jsonl` 文件双写；`LiteLLM`/httpx 等第三方 WARNING 起；关键日志带 `run_id/chapter_number/stage/version_id/db_path`，并与既有 `logs/chapter_runs/*.jsonl` 对齐 | DONE: `tasks/174-logging-system-foundation-DONE.md`；字段约定完成；三边重建实跑演示挂起至 175 后补跑 |
| 175 | 成本追踪与预算熔断 | 🔄 进行中 | 阶段 A-C 代码完成：`llm_call_usage` 表+repo（`3d72774`/`407ecbc`）、call_llm 拦截+agent 归因（`9caa1c5`/`6a92fea`）、run_cost_budget 双检查熔断+total_cost 接线（`324c028`/`8a5c799`）、report 成本视图（`f2982f8`/`92e4e81`）；全量 2869 passed、ruff 绿；终审通过 | 阶段 D 实跑验收待 API 预算确认：熔断实证 + scifi end10 + 173/174 挂起项补跑 |
| 176 | Windows 防卡 wrapper 工具化 | ◻ | V5 文档协议 → `scripts/run_with_timeout.ps1`（PowerShell Job + 硬超时） | 用 wrapper 跑通一次短窗口实跑 |

### V9.2 交付与发布

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 177 | songyan export 正文导出 | ◻ | accepted head 正文 + 弧/卷元数据；`--format md/txt --by arc/flat`；收编任务脚本里的 `_export_prose()` 复制粘贴为正式 service | 从既有 Ch100 DB 导出完整可读书稿 |
| 178 | wheel 打包与资源加载修复 | ◻ | 将 `prompts/`、`genres/`、`creative_modes/`、`project_templates/`、`prompts/literary_plugins/` 等运行资源纳入 wheel；优先用 `importlib.resources` 或等价 package-data 方案统一 loader，保留测试可注入外部目录能力；全量扫描并更新所有根目录相对路径引用，不把“移动目录后自然正确”作为前提 | 干净 venv `pip install .` 后，在非仓库 cwd 跑通资源枚举、`create-project --template scifi`、scifi 1-3 章；7 个 genre、4 个 mode、全部模板、prompt cards、literary plugins 可加载；全量测试绿 |
| 179 | CLI 体验修复 | ◻ | run 成功回显 run_id；`run --mode-id` 默认回读 `project.mode_id`；README CLI 表补 `index` 与全参数 | 三坑各有测试或实跑证据 |
| 180 | songyan doctor 环境自检 | ◻ | .env / API key 连通性 / DB 可写 / 模板目录完整性；key 错误在首次 LLM 调用前给可读提示 | 构造坏环境逐项验证提示质量 |
| 181 | CI 上线与测试清零 | ◻ | GitHub Actions（ruff + mypy + pytest 分层：unit 默认、integration 可选）；修 `tests/cli` 4 个既有失败；移除 `pyproject.toml` 对 `tests/cli` 的默认忽略或在 CI 中单独强制运行；README tests badge 改生成机制 | CI 全绿；本地 `python -m pytest tests/ -q` 与 CI 覆盖口径一致或差异显式文档化；badge 不再手改 |

### V9.3 爬坡工具链

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 182 | 五门判定器与段审计收编 | ◻ | `.tmp/vdim_compare.py` / `.tmp/segment_audit.py` → `scripts/`，`--genre/--db/--baseline/--up-to` 参数化；sci-fi 基线 JSON 迁出 `.tmp/` 到正式位置；预算/CED/overdue/health/completeness 判定函数零口径改动，I/O、路径解析、报告渲染可重构 | xuanhuan/wuxia 既有 Ch100 DB 重放，判定结果与归档报告一致；参数化版本与 `.tmp` 原脚本同库输出逐项对齐 |
| 183 | Profile 调参 CLI | ◻ | `songyan profile show/diff/upsert --genre <g>`，`GenreRuntimeProfileRepository` 既有 API 薄封装；三列渲染（注册表基线/DB 覆盖/生效值）；文档化 172j 降回边界 | 一次 DB 覆盖调参全程不改代码完成 |
| 184 | genres/creative_modes JSON Schema | ◻ | 参照 `project_templates/_schema.json`；加载时校验（可选 strict） | 7+4 个 JSON 全部过校验；坏样本被拦 |

### V9.4 urban 标定

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 185 | urban 短窗口标定实跑 | ◻ | base_budget 候选 12000 → 13000 →（必要时）15000 实跑标定；先确认 resolve 机制生效（`foreshadowing_resolved` 事件 > 0）再按实测 plant 密度定 floor 初值；T9=6 逐条复核（真问题修写作/规则侧，非系统性原因只进诊断报告，不计 PASS）；标定迭代走 183 CLI，标定值落注册表后跑 scifi end10 回归 | end15 emergency 不连触、峰值 <1.0、clean rerun T9=0；标定值与证据落盘 |

（185 不依赖全部 A 组完成，但有硬前置：173/174 完成后才允许真实 LLM 实跑；调参迭代走 183 的 CLI，不改代码；长窗口或高成本标定前应先完成 175。）

### V9.5 urban Ch100 爬坡

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 186 | urban Ch100 任务书 | ◻ | 目标 / 前置证据（185 数据）/ 分段验收 / 撞墙路由表（预算墙→base_budget；overdue 墙→先查 resolve 再调 floor；CED 墙→热点章+角色密度；health 墙→weight 校准）；冻结口径引用 172b §1.1 | 任务书评审通过才准入 187（治理规则：先补任务文档再开跑） |
| 187 | urban Ch100 爬坡执行 | ◻ | `TEMPLATE_ID=urban RUN_ID=187` 复用 `scripts/run_172b_ch100_climb.py`，25 章一段（arc 边界）；段边界正式五门 + 段审计，任一 FAIL 冻结现场 → 定点修复（按 187.p/q… 登记）→ 机制修复后 clean rerun | Ch100 五门 PASS（B 组判据）+ 终判报告落盘 |

### V9.6 收口

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 188 | V9 收口与归档 | ◻ | STATUS / AGENTS / README / 本文更新；任务文档归档 `archive/v9/`；V10 方向登记 | V9 全量闭环，文档事实源一致 |

---

## 关键输入数据

### urban 标定输入（172k 实跑，2026-07-18）

| 指标 | urban end15（注册表全默认） | 对照：xuanhuan end10（已标定） |
|------|------|------|
| accepted | 15/15，0 halt | 10/10，0 halt |
| budget 峰值 | 0.982 | 0.9755 |
| **before_emergency 峰值** | **1.2792（贴近 1.3 halt 线）** | — |
| **emergency 次数** | **17 次（15 章连续触发）** | **0 次** |
| overdue | 1 | 0 |
| CED/1k | 3.6776 | 5.3012 |
| **T9** | **6（timeline_conflict 4 + meta_tag_leak 2）** | 0 |

结论：urban 与 xuanhuan Ch8 同根因——溢出发生在不可裁核心（genre_rules token 成本 urban 与 scifi 同级 −1.5%，但默认 base_budget=8000 的爬坡起点太低）；杠杆是抬 base_budget（xuanhuan 路径 12000→13000→15000 实跑标定），不是调分区权重。

### sci-fi Ch1-100 逐段基线（172b 冻结，V9 B 组对标口径）

| checkpoint | budget_peak | overdue | health | CED/1k（旧宽口径，判定时由五门工具按 consistency-only 现算覆盖） |
|---:|---:|---:|---:|---:|
| Ch25 | 0.989 | 61 | 9.2 | 9.33 |
| Ch50 | 0.989 | 110 | 9.4 | 9.28 |
| Ch75 | 0.989 | 136 | 9.9 | 9.46 |
| Ch100 | 0.989 | 168 | 10.0 | 9.13 |

### 体裁注册表现状（`genre_runtime_profile_repo.py`）

| 字段 | scifi | xuanhuan | wuxia | urban |
|---|---|---|---|---|
| base_budget / ramp | 8000 / 250 | 15000 / 250 | 10500 / 250 | **8000 / 250（未标定）** |
| foreshadowing_horizon_floor | 0 | 48 | 48 | **0（待 185 标定）** |
| character_decay.focal_gaps | 3/10/30 | 8/20/60 | 8/20/60 | 3/10/30 |
| continuity.health_overdue_weight | 0.3 | 0.3 | 0.15 | 0.3 |

---

## 依赖关系与执行纪律

```
V9.1  173 ──► 174 ──► 175 ──► 176          （长跑可靠性，相互弱依赖，按序执行）
V9.2  177 ──► 178 ──► 179 ──► 180 ──► 181  （交付与发布；178 打包为连锁影响最大单项，独立验收）
V9.3  182 ──► 183 ──► 184                  （工具链收编；182 重放回归依赖既有 Ch100 DB 在位）
V9.4  185                                  （urban 标定；硬前置 173/174，调参前置 183；可在 V9.3 后期并行启动）
V9.5  186 ──► 187                          （任务书评审准入爬坡；撞墙修复 187.p/q…）
V9.6  188                                  （收口）
主链：V9.1 → V9.2 → V9.3 → V9.4 → V9.5 → V9.6；scifi end10 回归贯穿全程
```

- **173/174 是一切真实 LLM 实跑的硬前置，当前代码级前置已完成**：挂死无兜底、应用日志不落盘时跑标定实跑，等于重演 172k 的事故场景；无 LLM 的纯重放/静态工具开发不受此限制。真实 scifi end10 / 三边重建演示因成本与耗时控制，顺延到 175 后补跑。
- **175 是长窗口与高成本标定的前置**：185 的短窗口摸底可在 173/174 后启动，但进入多轮标定或 187 Ch100 前必须具备成本追踪与预算熔断
- **185 为什么可以并行**：短窗口标定依赖既有 `scripts/run_172a7_genre_validation.py`，不等全部交付发布任务；但调参迭代应走 183 的 CLI，故排在 V9.3 后期
- **先补任务书再开跑**（沿用 V8 治理规则 4）：186 评审通过前不得启动 187
- **overdue 墙先查 resolve 再调 floor**：禁止用调 floor 掩盖根因（172c.r 纪律）
- **机制修复后必须 clean rerun**：诊断 DB 一律不作终判样本（172c 纪律）
- **五门工具收编零口径改动**：182 搬运可重构 I/O、路径解析和报告渲染，但预算/CED/overdue/health/completeness 判定函数不改，双体裁 DB 重放回归作证
- **质量同标，不放宽口径**：urban 的 T9/health/overdue/CED 与 sci-fi 用同一套冻结口径
- **段边界早停纪律**：任一段五门不过就不继续烧后续章节，先冻结现场再路由定点修复
- **任务编号治理沿用 V8 规则**：编号是 trace id 不是执行顺序；撞墙修复字母后缀只在父任务内有序；不为治理本身新增数字任务号

---

## V9 明确不做（划界）

| 项 | 归属 |
|----|------|
| 跨体裁 Ch200 验证 | V10（与优秀度信号包捆绑；基线需先扩到 Ch200 checkpoint、口径需冻结） |
| 优秀度信号包：跨章同质化指数、中文 AI 腔规则包、judge 偏差对策、perplexity gate、style extraction → style card、角色声纹锚点 | V10（2026-07-18 调研清单已备） |
| 结构升级：章级 KG 图 diff 矛盾检测、FactTrack validity interval、Storyline Tree | V10 spike 候选（调研报告 `docs/reports/v8-literature-and-landscape-review.md` 储备） |
| GateConfig 构建时序重构（`cli/main.py` genre 未知即建全局 config） | V10 或更晚（不阻塞本阶段调参与爬坡） |
| max_* 锚定方案（动态曲线基准从 profile 派生） | 仅当 185 标定证明需要时立项 |
| DB 稀疏覆盖存储（解决 172j 降回边界的真正修法） | V10 或更晚 |
| 小说特化微调（DPO/GRPO）、多 agent 仿真生成、Temporal durable execution 迁移 | 调研反面清单，不做 |
| 修订停滞检测、LiteLLM proxy fallback 链、Langfuse tracing、LLM 幂等缓存 | 工业水位清单其余项，V9 只取成本追踪与熔断，其余按实际痛点后续评估 |
| 项目备份/迁移、RAG 质量闸口、literary plugin 注册机制、迁移版本账本、evals 双层命名整理 | 已知缺口，归 V10 或按需 |
| 新增 Agent / Workflow 节点 | 沿用 AGENTS.md 边界，不新增 |

---

## 风险与对策

| 风险 | 对策 |
|------|------|
| API 成本：标定 + 爬坡约 100+ 章实跑 | 173/174 后只做低成本短窗口摸底；175 成本追踪落地后再进入多轮标定与 Ch100；沿用分批窗口纪律 |
| 挂死归因错误：兜底掩盖真因，长跑积累资源泄漏 | 173 诊断先行；真修与兜底分开验收 |
| 178 资源打包连锁破坏：运行资源入 wheel 碰大量根目录相对路径 | 独立任务；优先统一资源 loader；全量测试 + scifi 短窗口实跑回归；非仓库 cwd 加载矩阵逐项验证 |
| 182 收编口径漂移 | 判定函数不改；I/O 重构与口径函数分离；xuanhuan/wuxia 双 DB 重放回归 |
| urban 出现新墙（都市对话密度、现代设定一致性为未知域） | 172c 纪律：段边界早停、定点修复、clean rerun；预期预算压力小于 xuanhuan（genre_rules token −1.5%），主要不确定性在 T9 与伏笔密度 |
| 实跑进程退出挂死（172k 已复现两次） | 173 修复前不跑长窗口；短窗口实跑后人工核对进程状态 |

---

## 文档入口

- V9 任务事实：`tasks/V9-README.md`（本文）
- V9 各任务文档（开工前补写）：`tasks/173-*.md` … `tasks/188-*.md`
- V8 历史事实：`tasks/V8-README.md`；归档 `archive/v8/INDEX.md`
- V9 中篇爬坡冻结口径参照：`archive/v8/tasks/172b-xuanhuan-ch100-climb.md` §1.1
- urban 标定输入详情：`archive/v8/tasks/172k-c-dimension-evidence-closure.md`
- GenreRuntimeProfile 机制与调参语义：`archive/v8/tasks/172a-v8-genre-runtime-profiles.md`、`archive/v8/tasks/172j-budget-pruner-max-shadowing-fix.md`
- 长调研报告（V10 储备）：`docs/reports/v8-literature-and-landscape-review.md`
- 项目状态：`docs/STATUS.md`；文档路由：`docs/INDEX.md`
- 开发规范：`AGENTS.md`

# V15 Task 总索引

> **阶段**: 导入已有小说续写
> **定位**: V15 是新的用户路径阶段，目标是把外部已有小说"语义编译"成 Songyan 项目——逐章回放 SettlementExtractor 建立 SQLite 事实库，然后从第 N+1 章进入正常续写流水线。这是 Songyan settlement 架构红利的兑现，不是新产品线。
> **当前口径**: V14 成本路由是 V15 的前置（导入一本 200 章的书 = 200 次 settlement 调用）。V15 不改变生成管线本身，只新增导入路径。
> **状态**: 规划完成，未启动。首个任务为 Task 234 V15 import pipeline audit。V15 启动前 V14 必须闭环。

---

## 背景结论

2026-09 同类项目调研结论：

- 头部同类 InkOS（旧书导入续写）和 ainovel-cli（`/import` 语义编译管线：ingest → segment → analyze → synthesize → publish）均已实现导入续写，属于用户真实需求的 table stakes。
- Songyan 的 settlement 架构天然适合做这个：导入 = 对已有正文逐章执行 SettlementExtractor（只提取事实，不生成），写出的就是标准的 character_states / settings / foreshadowings 事实库，与原生生成项目结构完全一致。
- 相比竞品的文件型真相文件，Songyan 导入后的事实库直接享有既有纪律：append-only 版本、事务化写入、正文证据回查、CED/T9 可度量。

关键判断：这是 V13/V14 之后唯一值得做的大块用户路径扩张，且是架构红利而非架构负担。

---

## 一句话目标

> 让外部技术用户把一本已有小说（txt/md）导入为 Songyan 项目，系统自动完成章节切分、逐章事实回放和事实库建立，用户确认后从第 N+1 章进入正常生成流水线，续写章节的 CED 不高于同体裁原生生成 baseline。

---

## V15 硬边界

- 导入的章节**只走 settlement 语义**：标记为 accepted，不触发 revision / rewrite / audit 流。
- 导入不覆盖、不修改源文件；源文件只读。
- 导入建立的事实库与原生生成共用同一 schema 和同一套 settlement 完整性约束（`old_value` 一致性、`source_quote` 正文存在性、`setting_key` 唯一性、`closing_value` 公式校验、`source_version_id` 必填）。
- 章节切分结果必须经人工确认后才进入回放；切分可人工干预后重放，不自动硬切。
- 回放失败可断点续跑，单章失败不污染已完成章的事实库。
- 续写阶段（N+1 章起）走正常流水线，无任何特殊豁免。
- 不新增核心 Agent；导入管线复用 SettlementExtractor / SummaryWriter 既有实现。
- SQLite 仍是唯一长期事实源。
- 不把 report-only / spike 信号接入导入或续写路径。

允许的改动：

- 新增导入管线模块（切分、回放、断点续跑）。
- 新增 CLI 子命令（如 `songyan import`）。
- chapter_versions 增加导入来源标记（元数据字段，内容仍 append-only）。
- 顺路执行 217 review 的 P2 重构 backlog 中与回放路径直接相关的部分。

---

## 导入管线阶段（规划草案，Task 234 冻结）

```text
ingest    源文件快照（指纹绑定，只读原文）
   ↓
segment   章节切分（产出章节边界清单，停下等人工确认）
   ↓
replay    逐章 SettlementExtractor 回放（只提取事实，不生成；断点续跑）
   ↓
synthesize 全书级归纳（体裁 profile 选择、主角档案确认、世界观汇总）
   ↓
publish   人工验收后发布为正常项目，进入第 N+1 章续写
```

每个阶段的中间产物落盘并按输入指纹绑定：中断后重跑只补缺失部分，不重复调用 LLM。

---

## 验收矩阵

| 组 | 验收目标 | 通过标准 |
|----|----------|----------|
| A | 切分可控 | 章节边界清单经人工确认后才回放；切分错误可干预后局部重放 |
| B | 事实库合规 | 导入章节的 settlement 通过全部既有完整性约束，无豁免路径 |
| C | 断点续跑 | 回放中途 kill 后重跑只补缺失章节，不重复 LLM 调用 |
| D | 单章隔离 | 单章回放失败有明确错误和恢复路径，不污染已完成章事实 |
| E | 续写质量 | 导入后续写窗口的 CED 不高于同体裁原生生成 baseline |
| F | 既有守护项 | `pytest tests/` 全绿、ruff 通过，不破坏 V11-V14 已验收路径 |
| G | 成本可控 | 回放成本在 V14 路由配置下有记录，report 可区分回放与生成成本 |

---

## Task 拆解

| Task | 名称 | 状态 | 目标 | 依赖 |
|------|------|:----:|------|------|
| 234 | V15 import pipeline audit | TODO | 只读审计 SettlementExtractor 对非生成正文的适用性、章节切分策略选项、断点续跑机制，冻结管线设计 | V14 closure |
| 235 | 章节切分与人工确认 | TODO | 实现 segment 阶段：章节边界识别、清单输出、人工确认/干预/重放 | 234 |
| 236 | 逐章 settlement 回放 | TODO | 实现 replay 阶段：只提取不生成、断点续跑、单章失败隔离 | 234/235 |
| 237 | import CLI 与全书级归纳 | TODO | `songyan import` 命令、ingest/synthesize/publish 阶段、体裁 profile 与主角档案确认 | 235/236 |
| 238 | 导入续写验收 | TODO | 用真实样本导入 + 续写窗口，对比 CED 与原生 baseline，产出验收报告 | 237 |

---

## Task 234: V15 Import Pipeline Audit

目标：

- 审计 SettlementExtractor 对"非本系统生成正文"的适用性：prompt 假设、体裁 profile 依赖、字符长度边界。
- 审计章节切分的策略选项（规则切分 / LLM 语义切分）及各自失败模式。
- 审计断点续跑的既有机制（run log / checkpointer）能否复用。
- 冻结管线阶段设计与验收矩阵细节。

测试：

- 不改 runtime，纯审计。
- 审计报告必须回答：settlement 对导入正文的失败模式有哪些，分别在哪一阶段拦截。

---

## Task 235: 章节切分与人工确认

目标：

- 产出章节边界清单（章节号、标题、起止位置），落盘可审查。
- 人工确认后才进入回放；干预后可对受影响区间局部重放。

测试：

- 切分产物可序列化、可 diff。
- 未确认状态下回放入口被拒绝。

---

## Task 236: 逐章 Settlement 回放

目标：

- 逐章执行 SettlementExtractor，写入标准事实库，章节标记为导入 accepted。
- 断点续跑：按输入指纹幂等，重跑只补缺失。
- 单章失败隔离：记录失败原因和恢复建议，不阻塞已完成章。

测试：

- 回放产出通过全部 settlement 完整性约束。
- kill 恢复测试：中断后重跑不重复 LLM 调用。
- 导入章节的 chapter_versions 带来源标记，内容 append-only。

---

## Task 237: import CLI 与全书级归纳

目标：

- `songyan import` 串起 ingest → segment → replay → synthesize → publish。
- synthesize：体裁 profile 匹配确认、主角档案人工确认、世界观汇总审查。
- publish：人工验收后项目进入正常可用状态。

测试：

- 每个阶段的中断恢复路径有演练证据。
- publish 前项目不可进入 `songyan run`。

---

## Task 238: 导入续写验收

目标：

- 用真实样本（建议先短篇 20-50 章级别）完整走导入 → 续写窗口。
- 对比续写窗口 CED 与同体裁原生生成 baseline。
- 产出验收报告，含 run_id、回放成本、CED 对比和已知限制。

测试：

- 验收报告引用可复现的 run_id 和 report。

---

## 风险与对策

| 风险 | 对策 |
|------|------|
| settlement 对非本系统正文提取质量差 | Task 234 审计先行，失败模式明确后再实现；单章失败隔离 |
| 切分错误导致整本书事实错位 | 人工确认闸门 + 局部重放，不自动硬切 |
| 回放成本高 | V14 per-role 路由前置；回放可用便宜模型，report 区分回放成本 |
| 导入被当作"质量豁免通道" | 硬边界：导入章节只提取不审查，续写章节走完整管线 |
| 源文件格式混乱（GBK、无章节标题） | ingest 阶段显式报错与恢复建议，不猜测 |

---

## 与前置阶段的关系

- V11 的 backup/restore 和 run bundle 为导入路径提供既有的资产保护和诊断能力。
- V13 公开的口径文档是验收矩阵 E 的判定依据：CED baseline 定义以 V13 文档为准。
- V14 是 V15 的成本前置：没有 per-role 路由，200 章规模的回放成本不可接受。
- V12 的启动校准成果（plan review、runtime validation）在续写阶段正常生效，导入路径不豁免。

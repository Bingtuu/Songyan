# 227 · PRD 对齐修订 + 旧测试裁决规则成文

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD §4.1 / §4.3 / §6.3 / §9.2 / §13；tests/README.md；来源 = 全量评审后的整体分析（2026-11-07） |
| 预估 | 一个切片（纯文档） |

## 目标

消除权威链顶层文档与已落地实现之间的漂移（PRD 字面落后于 M1/M2/M3 的已接受决策），并把「旧 lineage 测试与已接受 M 文档语义冲突」的裁决规则成文。只改文档，不改代码。

## 步骤

- [x] 建任务 + HANDOFF 指向
- [ ] PRD 修订（逐条见下）
- [ ] tests/README.md 加「旧测试裁决规则」节
- [ ] 只读 review（diff 级）
- [ ] 提交；归档；同步 STATUS / HANDOFF

### PRD 修订清单（task 226 全量评审 + 整体分析确认的漂移点）

1. 状态头：「待 owner 书面接受」→ 已接受（2026-11-01，#27）。
2. §4.1 Canon 行：属性 source 口径 `plan|human` → `plan|human|extract`（tech-m2 B5）。
3. §4.1 Variant 行：「还没有」→ `chapter_variants` + `variant *` 命令组（M3 步 1–5 已落地）。
4. §4.1 ConsistencyReport 行：「作者向 check 还没有」→ 已有（M1）。
5. §4.1 Proposal 行：「语义要建」→ M2 已建（pending + source=extract）。
6. §4.3：补注——M1 锁定三态 `pending/approved/rejected`，`accepted` 为非持久提示，无持久第四态。
7. §5 里程碑表 M1 行与 §6.3 主路径、`§9.2` 命令表面：`triage` 命名对齐实际命令面（`edit / accept(非持久) / confirm / dismiss`，未注册 `triage` 子命令）。
8. §13 文档关系表：本文状态行同步「已接受」。

### tests/README.md 新增节（旧测试裁决规则）

- 当旧 lineage 测试断言的行为与已接受的 PRD / tech-m* 文档冲突时，**已接受文档胜出**。
- 同一切片（同一提交）内把测试改写到新语义，并在任务完成总结里记录：被改测试名、旧断言、新断言、依据的文档条款。
- 禁止把测试改弱（删断言、放宽条件）来迁就实现；改后必须覆盖同一路径。
- 先例：task 226（`test_172cr` / `test_241` / `test_settlement_extractor` 的 resolve 直写断言 → 提案语义，依据 tech-m2 §3.2/§4.3.3/B3）。

## 验收标准

- [ ] PRD 8 条修订逐条落实，无其他内容改动。
- [ ] tests/README.md 新节包含裁决规则三条 + 226 先例。
- [ ] 只读 review 通过（无遗漏漂移点、无越权改动）。
- [ ] 不触碰 `src/`、`tests/` 代码、`pyproject.toml`。

## 完成总结（DONE 时填写）

**状态**：DONE（2026-11-07）。纯文档修订，一次提交。

**做了什么**：
- PRD 修订 11 处：状态头与 §13 改为「已接受（2026-11-01）」；§4.1 Canon 行 source 口径补 `extract`（tech-m2 B5）；Variant / ConsistencyReport / Proposal 三行刷新为已落地现状；§4.3 补 M1 锁定口径段（三态 CHECK、accept 非持久、dismiss 落 rejected）；§4.1 末段「approval_status 两态」改为三态已落地 + superseded/hardness 未采用说明；§4.2 标题改为「variant 表已于 M3 落地」；§5 M1 行、§6.3 主路径、§9.2 命令表面的 `triage` 命名对齐实际命令面（edit / accept 非持久 / confirm / dismiss）。
- tests/README.md 新增「Legacy semantics vs accepted M-docs（裁决规则）」节：同切片改写 / 完成总结记录旧断言新断言与依据条款 / 禁止改弱，附 task 226 先例。

**验收**：只读 review（diff 级）通过——8 项修订逐条核实与落地实现一致、无越权改动；review 另发现 3 处同类漂移（PRD:127、PRD:129、tests/README:66）已同切片修复。未触碰 `src/`、`tests/` 代码与 `pyproject.toml`。

**遗留**：无。P0-2（promise evidence 落库）、P0-3（plan 模型默认值）、P1-5（旧 lineage 工作区文件清理）不在本任务范围，待另行立项。

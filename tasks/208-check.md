# 208 · check 只读规则报告（W6）

| 项 | 内容 |
|---|---|
| 状态 | DOING |
| 关联 | PRD 6.4；tech-m1 §4.3 / §5 步 4 / §6；W6 |
| 预估 | 一个切片 |

## 目标

人可通过 `songyan check --project-id --chapter [--json]` 对一章已存正文做只读规则检查：薄包装 `run_plan_fact_gate`；`chapter_text` 取自 `ChapterHead.accepted_version_id` → `ChapterVersion.content`；`AttributeExtract` 仅夹具/注入，不从散文现抽；不写库、不调用 confirm。本切片不做步 5（today next / W0 e2e）。

## 步骤

- [x] 测试先写：`tests/cli/test_check_command.py`（缺库/缺项目 exit 1；无章可查 exit 2；注入不一致报告字段 + exit 2；过门 exit 0 且无「可以发表」；plan 行不变；不发明摘录；无 confirm）
- [x] 实现 `check` 并注册；Markdown / `--json`；可选 `--extracts-json` 夹具注入
- [x] 跑 tech-m1 §7 相关命令；开 PR，不合并、不 APPROVE

## 验收标准

- [x] CLI：`songyan check --project-id TEXT --chapter INT [--json]`
- [x] 无 head / 无 accepted_version / 缺或空正文 → exit 2「无章可查」
- [x] 注入 AttributeExtract 与已批准属性不一致时，报告点名实体、键、圣经值、正文侧值、严重度
- [x] 检查前后 plan_* 行数与 approval_status 不变；不调用 confirm
- [x] 门通过 exit 0，文案无「可以发表」；可提示另走 canon confirm
- [x] 不改 workflows / settlement_extractor；不升包版本；不做步 5

## 完成总结（DONE 时填写）

（合入后填写）

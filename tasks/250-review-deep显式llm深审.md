# 250 · review --deep（显式 LLM 深审，成本前置）

| 项 | 内容 |
|---|---|
| 状态 | TODO（tech-m4-followup 步 3；owner 已接受 B1–B8，2026-11-12） |
| 关联 | `docs/tech-m4-followup.md` §5 / B4 / B5 / B6；task 236 N3 写边界口径 |
| 预估 | 两个编码切片（成本门 + 深审合并）+ 一次真实模型复验（¥1 内） |

## 目标

`songyan review --project-id TEXT [--chapter INT] --deep [--yes] [--budget-cny FLOAT]`：在现网七源只读报告上追加 LLM 深审分区（同一 `ReviewFinding` 形状，source=`deep`）。不带 `--deep` 现网行为一字不动。成本前置（B4）；零写库（B5）；LLM 失败保留非 deep 分区（stderr 注明）。

## 关键口径

- **成本门（B4）**：预估费用（token 估算，现成工具）打印 → 交互 y/N；`--yes` 跳过；**非 TTY 且无 `--yes` → exit 2**；`--budget-cny` 硬上限（预估超限拒绝 exit 2；执行超支中断并保留已产出）。
- **输入三件套（B6）**：工作稿正文（head.current_version_id）+ 本章 approved 圣经 + 上一章 accepted 摘要（120 字截断，`_get_previous_summary` 现成）。
- **检查四条（B6）**：事实一致性（hard）/ 连续性（hard/warning）/ 复读复核（warning/info）/ 文风视角（info，措辞红线：只说「建议人复核」）。
- **归因**：`call_llm` 标准遥测，agent=`review.deep`；无第二记账。
- **exit**：0 = 报告（含发现，B11 同形）；2 = 成本门拒绝；1 = 缺库/缺项目/参数非法/LLM 失败（非 deep 分区照出）。

## 步骤

- [ ] TDD 切片 1：成本门（交互确认 / --yes / 非 TTY 拒绝 / 超预算拒绝），mock call_llm
- [ ] TDD 切片 2：深审装配（三件套输入 prompt、结构化 findings 映射 ReviewFinding、合并进报告分区）；零写库断言（表行数快照）
- [ ] 既有 review 测试原样通过（不带 --deep 零变化）
- [ ] 真实模型复验 1 次（可并入 249 冒烟或单独，¥1 内，费用与预估同量级）
- [ ] 全量回归 + ruff；完工同步 STATUS/HANDOFF；归档

## 验收标准

- [ ] 成本门四分支全锁死；非 TTY 无 --yes 必 exit 2
- [ ] deep findings 合并呈现，severity/source/message/evidence/location 齐
- [ ] 零写库 + 费用归因 agent=review.deep 逐行可查
- [ ] 不带 --deep 现网行为零变化
- [ ] 全量 pytest 绿 + ruff 绿；不 bump 版本
- [ ] 完工同步 `docs/STATUS.md` / `docs/HANDOFF-mew.md`；归档 `tasks/done/`

## 完成总结

（待 DONE 时填写）

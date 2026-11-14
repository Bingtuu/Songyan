# 265 · Context 断链修复（W2 定向注入 + 质量小项）

| 项 | 内容 |
|---|---|
| 状态 | DOING（2026-11-14；owner 批准选项 B 立项，评估文档 `docs/experiments/265-context-disconnect-eval.md`） |
| 关联 | 都市恐怖 dogfood 发现（`.tmp/dogfood-G-urban-horror-末班电梯-230946/frictions.txt` F1–F12）；tech-m4 B12（不动其语义） |
| 预估 | 5 个切片；一次 dogfood 复测（¥0.1 内）；回归全量 |

## 目标

修掉 writer context 三层断链（C2 storylines 零消费 / C3 角色背景丢弃 / C4 设定丢弃），让「人编辑故事线/角色/设定」对续写真实生效；W2 裸奔时给出可见提醒（不改 B12 兜底语义）；顺手修 C5（project 钩子无编辑面）、F9（抽卡字数无提醒）、F3（--title 回显旧值）。

## 步骤

- [ ] S1 定向注入：context 组装带 story_brief（书名+core_conflict+mainline_synopsis+themes+当前 arc goal+open threads）、character_roster（名字/类型/背景，主角全量+其余裁剪 200 字）、world_settings（setting_snapshots 描述）；writer 卡 1.1.1→1.2.0 新增三个版面变量
- [ ] S2 空定向提醒：`chapter continue` 在 bible 空 且 goal/brief 空时输出一行可见提醒（不阻断）
- [ ] S3 C5：`storyline edit outline` 增加 `--core-hook` / `--protagonist-background`，同步 project_setting 对应字段
- [ ] S4 F9：`variant generate` 产出低于校准字数下限时，槽位 quality_flag 标 `short` 并在输出中提醒
- [ ] S5 F3：`create-project --title` 成功回显打印应用后的标题
- [ ] S6 dogfood 复测：全新 .tmp 临时库，urban 模板 + 恐怖 storyline（不预置 canon），`chapter continue --chapter 1` 内容命中恐怖要素
- [ ] S7 回归 + 归档：默认收集全绿 + tests/cli 全绿 + ruff；归档 tasks/done + STATUS/HANDOFF 同步

## 验收标准

- [ ] S6 中 ch1 无需人工 canon 预置即命中 storyline 恐怖要素
- [ ] 全量回归绿（3654 基线 + 新增测试）；`tests/cli` 全绿；ruff 零告警
- [ ] 不越 B12（goal 兜底语义不变）、不加题材检查器、不自动选优
- [ ] STATUS/HANDOFF/AGENTS（命令表面如有新增选项）同步

## 完成总结

（待 DONE 时填写）

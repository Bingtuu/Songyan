# 233 · M3 步 6 — 闭环文案与文档同步

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-08） |
| 关联 | [tech-m3.md](../docs/tech-m3.md) §5 步 6（owner 2026-11-08 授权开工） |
| 预估 | 小切片（一条固定文案 + 文档同步） |

## 范围（tech-m3 §5 步 6 原文）

- [x] `today` 的 `next` 固定文案从 M2 口径改为提示抽卡（M3 步 1–5 已落地，`variant generate` 可提示）
- [x] STATUS / HANDOFF 记步次（M3 步 1–6）
- [x] 不声称 V1.0 完成；不 bump `0.5.0`；不注册 `continue` / `review` / `branch`

## 实施要点

1. `src/songyan/cli/commands/workbench.py` `_NEXT` 改为提示抽卡文案（PRD 口径：口语「抽卡」= 章内 variant；默认 N=2；不 auto-pick）。
2. TDD：先改 `tests/cli/test_workbench_commands.py` 与 `tests/cli/test_w0_e2e.py` 锁死的 `_NEXT`（看红），再改实现（看绿）。
3. 同步 `docs/STATUS.md`（一眼进度表 M3 步 6 行、已知限制里 today 文案条目）与 `docs/HANDOFF-mew.md`（下一闸门表述）。

## 验收标准

- [x] `today`（文本 + json）`next` 含抽卡提示，两处测试锁死。
- [x] 无版本 bump；无新 CLI 注册；`git diff` 不出现 `continue` / `review` / `branch` 命令。
- [x] 相关测试 + ruff / mypy 过；全量回归唯一允许失败为既有环境项。

## 完成总结

**状态**：DONE（2026-11-08）。

**做了什么**：

1. `workbench.py` `_NEXT`：M2 口径「…生成不在本命令。」→ M3 口径「…章内草稿走 variant generate 抽卡（默认 N=2，不 auto-pick）。」（隐式拼接满足 ruff E501；文本与 json 输出共用同一常量）。
2. TDD：两个测试文件的新 `_NEXT` 先红（3 failed）后绿（11 passed）。
3. STATUS/HANDOFF 步 6 同步；review 发现的 4 个文档一致性 major（步 6 未开旧表述残留 4 处）已同切片修复并复核清零。

**review**：首轮 4 major 均为文档旧口径残留，已修复；红线（无 bump / 无 continue/review/branch 注册 / 无 V1.0 声称）通过。1 条 follow-up：`docs/tech-m3.md:336`「下一闸门 = owner 授权再开步 6」为已接受文档、不在本切片授权范围，留 owner 决定是否同步。

**验证**：`tests/cli` 相关 11 passed；ruff / mypy 过；全量 `pytest tests/`（PYTHONUTF8=1）终验。

**附带环境评估结论**（详见 STATUS「环境项」条目）：`test_llm_http_timeout` 为负载敏感的时序 flake（非确定性依赖 bug）；`test_191_ch200_harness.py` 根因 = 子进程 locale 解码，一行修复建议已记录。

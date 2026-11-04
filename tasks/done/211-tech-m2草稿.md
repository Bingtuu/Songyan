# 211 · tech-m2 技术方案草稿（docs only）

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD M2 / W4 / W5 / §7.3；AGENTS 开工门 |
| 预估 | 一个 docs 切片 |

## 目标

起草 `docs/tech-m2.md` 并同步 STATUS / HANDOFF / INDEX / AGENTS / tasks，开 docs-only PR，供 owner 书面接受。不改 `src/` / `tests/`，不开 M2 编码。

## 步骤

- [x] 从 `origin/main` 开分支 `docs-tech-m2-draft`
- [x] 对照 PRD 与现码写出 tech-m2（绑定决策 B1–B6）
- [x] 同步配套状态文档
- [x] 提交并开 PR（不合并、不 APPROVE）

## 验收标准

- [x] `docs/tech-m2.md` 存在且标明 **草稿，待 owner 书面接受**
- [x] 无 `src/` / `tests/` / 工作流 / 结算器行为变更；`pyproject.toml` 仍为 `0.5.0`
- [x] 无 M2 编码任务 DOING；无 V1.0 完成声称

## 完成总结（DONE 时填写）

Docs-only 草稿已推送并开 PR。下一闸门：owner 书面接受 tech-m2 后，再按文内步 1 建编码任务。

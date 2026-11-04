# 212 · M2 步1 W5 只读（today 承诺计数 + canon show promise）

| 项 | 内容 |
|---|---|
| 状态 | DOING |
| 关联 | PRD §6.6 / W5；tech-m2 §5 步 1 / B3；S8 |
| 预估 | 一个切片 |

## 目标

M2 步 1：从 `foreshadowings` 只读 planted/due/overdue 计数与列表；`today` 含承诺计数；`canon show --kind promise` 列出开放承诺。不写库；不把承诺写成 Canon 事实；不泄漏 pending plan 行 as Canon。

## 步骤

- [ ] 测试先写：`tests/cli/test_workbench_promise_readonly.py`（及必要的 today/json 锁文案同步）
- [ ] `workbench.py`：复用 `ForeshadowingRepository.list_schedulable`（active + planted/due/overdue）
- [ ] 同步 STATUS / HANDOFF；跑 ruff + 相关 pytest；开 PR，不合并、不 APPROVE

## 验收标准

- [ ] 插入 overdue 夹具后 `today` 计数含它（text + json）
- [ ] `canon show --kind promise` 可见开放条目；默认 show 不把承诺标成 Canon
- [ ] 有 pending plan 行时，promise 视图与默认 Canon 段均不泄漏为已确认事实（S8 无关路径）
- [ ] 不写库；无 promise 命令组；无销账 / `--hard` / `content_stale` / extract source；包仍 `0.5.0`

## 完成总结（DONE 时填写）

（合入后填写）

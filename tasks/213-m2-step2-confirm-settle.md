# 213 · M2 步2 W5 人确认销账（canon confirm promise）

| 项 | 内容 |
|---|---|
| 状态 | DOING |
| 关联 | PRD §6.6 / W5；tech-m2 §5 步 2 / B3–B6；S3 |
| 预估 | 一个切片 |

## 目标

M2 步 2：人经 `canon confirm promise`（章号 + 证据）销账开放承诺，写入 `status=resolved` 与 `resolved_chapter` / `resolved_version_id`；未经 confirm 仍留在 open 集。复用 `foreshadowings` 与既有 confirm 挂载；不新开 `promise` 命令组。不做步 3+（`--hard` / `content_stale` / extract source / SettlementExtractor 权威漂移）。

## 步骤

- [ ] 测试先写：`tests/cli/test_canon_confirm_promise.py`（PRD §6.6 验收 1–3；无 confirm 不清 open；confirm 后追溯列；缺 accepted 版本 exit 2）
- [ ] `canon_write.py`：挂 `confirm promise`；解析章 `accepted_version_id`；调用 `ForeshadowingRepository.update_status`
- [ ] 轻量同步 STATUS / HANDOFF / tasks README；跑 ruff + 相关 pytest；开 PR，不合并、不 APPROVE

## 验收标准

- [ ] `canon confirm promise --foreshadowing-id … --chapter N --evidence …` 成功后 status=resolved，回填 resolved_*；open / today / show promise 不再含该条
- [ ] 未经 confirm（含模拟「提案未确认」）该条仍在 open 集
- [ ] 无第二伏笔表；证据必填；缺章 accepted 版本 exit 2；缺库/缺项目/坏 id/空证据 exit 1
- [ ] 无 `--hard` / `content_stale` / extract source / promise 命令组；包仍 `0.5.0`

## 完成总结（DONE 时填写）

（合入后填写）

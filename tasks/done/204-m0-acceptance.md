# 204 · M0 代码验收 PASS

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD 6.2；tech-m0 §6–7；W0 只读半边 |
| 预估 | 验收记录（无新代码） |

## 目标

在 `main` 上确认 M0 步 1–4 与 tech-m0 §6–7 的代码验收通过，并留下可检索的归档，供 STATUS / HANDOFF 引用。不声称 V1.0 完成，不升包版本。

## 步骤

- [x] 核对 tip：`main` @ `80f4107`（#32 文档指向验收之后）
- [x] 记录既有验收证据（owner / 代理在 tip 上已跑）
- [x] 同步 STATUS / HANDOFF：下一闸门改为接受 tech-m1，再开 M1 编码

## 验收标准

- [x] 步 1–4 均已在 `main`（#28–#31）
- [x] tech-m0 §6–7 代码项 PASS（见完成总结）；S6 不在代码验收内
- [x] 无 pyproject 版本 / migrations.py / workflows/ / settlement_extractor 相对 main 的行为漂移（本记录不引入此类改动）

## 完成总结（DONE 时填写）

在 `main` `80f4107` 上的代码验收证据：

- `ruff` OK
- `tests/cli/test_workbench_commands.py`：10 passed
- plan-related：38 passed
- 默认 pytest：3504 passed（2 skipped / 1 xfailed）
- §6 行为由都市灵异夹具 CLI 测试覆盖；S6 不计入代码验收

遗留：owner 书面接受 [docs/tech-m1.md](../../docs/tech-m1.md) 之后，再开第一刀 M1 编码。本记录不改 `src/` / `tests/` 行为。

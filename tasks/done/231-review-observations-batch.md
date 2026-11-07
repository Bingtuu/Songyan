# 231 · 评审观察项清理批

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | 全量评审 observation 清单（`docs/superpowers/plans/2026-11-07-m0-m3-review-audit.md`） |
| 预估 | 一个切片 |

## 范围（修 5 项，记录 3 项不修理由）

- [x] 建任务 + HANDOFF 指向
- [x] 1. migration 崩溃窗口：`_rebuild_plan_table_approval_check` 建临时表前先 `DROP TABLE IF EXISTS`（进程死在 CREATE 后 DROP 前会留孤儿表卡死下次迁移）
- [x] 2. `check.py` 宽 `except Exception` 收窄为 `(ValidationError, TypeError, ValueError)`
- [x] 3. `variant` 文本输出 `stale=` 改 `stale_vs_canon=`（与 `content_stale` 防混，STATUS 已锁此文案纪律）
- [x] 4. `get_by_slot` 的 `LIMIT 1` 补 `ORDER BY created_at ASC`（确定性）
- [x] 5. `default_slot_draft` 成本/模型按 role="writer" 解析出的实际模型计价与回填（原硬编码默认模型，路由到别的模型时低估）
- [x] 6. 记录不修：`test_llm_http_timeout` 本机失败 = litellm/httpx 在 Windows 下不对悬挂 socket 应用 request_timeout（client 代码已正确传参），属依赖层环境问题，需维护者单独调查
- [x] 7. 记录不修：`mark_content_stale` 刷 `updated_at` 语义偏移（behavior 变更，需 owner 拍板）
- [x] 8. 记录不修：variant generate 重复指纹/圣经加载（纯性能，收益低风险小，不值得在本批动）
- [x] TDD（1/3/5 有行为测试）→ 全量验证 → review → 提交

## 验收标准

- [x] 孤儿临时表场景下 run_migrations 成功（测试锁死）。
- [x] variant list / pick 文本输出含 `stale_vs_canon=`（测试锁死）。
- [x] default_slot_draft 的 SlotDraft.model = writer 角色解析出的实际模型（测试锁死）。
- [x] `--extracts-json` 非法输入仍报「无效」且其余行为不变。
- [x] `pytest tests/` 全绿（允许既有 `test_llm_http_timeout` 环境失败）；ruff / mypy 过。

## 完成总结（DONE 时填写）

**状态**：DONE（2026-11-07）。

**做了什么**：
1. migration 崩溃窗口：`_rebuild_plan_table_approval_check` 建 `__m1_rejected` 临时表前先 `DROP TABLE IF EXISTS`（孤儿表场景迁移测试锁死；DROP 仅在待迁移分支，幂等不变）。
2. `check.py` 宽 `except Exception` 收窄为 `(ValidationError, TypeError, ValueError)`。
3. `variant` 文本输出 `stale=` → `stale_vs_canon=`（list/pick 两处；与 `content_stale` 防混）。
4. `get_by_slot` / `pick_slot` / `set_status` 三处裸 `LIMIT 1` 补 `ORDER BY created_at ASC`（review 跟进项）。
5. `default_slot_draft` 用 `resolve_llm_config("writer").model` 计价并回填 `SlotDraft.model`（含计价断言与 role 覆盖隔离的测试）。

**review**：通过；两条 Low（pick_slot/set_status 裸 LIMIT、slot draft 测试环境脆弱）与一条提示已同切片修复。

**记录不修**：`test_llm_http_timeout`（litellm/httpx 在 Windows 下不对悬挂 socket 应用 request_timeout，client 传参已正确，依赖层问题需维护者单独调查）；`mark_content_stale` 刷 `updated_at`（behavior 变更需 owner 拍板）；generate 重复指纹加载（纯性能）。

**验证**：三个 RED 测试先红后绿；相关文件 33-42 passed；ruff / mypy（198 文件）全绿；goal 终验全量回归通过（唯一失败为上述已知环境项）。

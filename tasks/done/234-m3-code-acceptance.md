# 234 · M3 §6–7 代码验收声称

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-08） |
| 关联 | [tech-m3.md](../docs/tech-m3.md) §6 验收清单（11 条）+ §7 验证命令；owner 2026-11-08 授权 |
| 预估 | 文档切片（声称 + 证据指针；无代码改动） |

## 范围

- [x] 跑 tech-m3 §7 验证命令全集并留证据
- [x] 对照 §6 清单 11 条逐条指认证据（测试 / 任务文档）
- [x] STATUS / HANDOFF 写「M3 §6–7 代码验收 PASS」及证据 tip
- [x] 不声称 V1.0 完成；不 bump；真实模型冒烟仍另开维护者任务（§7 原文）

## 验收标准

- [x] §6 清单 11 条每条有证据指针。
- [x] §7 命令输出全绿（允许已记录环境项）。
- [x] STATUS 一眼进度表「M3 §6–7 代码验收」行转 PASS。

## §6 清单证据映射（11 条）

| # | 条目 | 证据 |
|---|------|------|
| 1 | 默认 N=2；generate 后无自动 picked | `test_variant_generate.py::test_generate_n2_writes_two_generated_no_pick` |
| 2 | 同章至多一 picked | `tests/db/test_chapter_variants.py` 双 picked 守卫 + `test_variant_pick_abandon.py` |
| 3 | pick 前后 plan_* approved 不变、无 canon 副作用 | `test_variant_pick_abandon.py` pick 前后 approved 集合断言 |
| 4 | 新 generate 不 UPDATE 已 picked 正文 | `test_variant_generate.py::test_generate_does_not_update_existing_picked_content` |
| 5 | abandon 软删、正文可读 | `test_variant_pick_abandon.py` |
| 6 | Canon 变更后 stale_vs_canon=1；stale pick 拒（exit 2） | `test_variant_stale_cost.py` / `test_check_stale_report.py` |
| 7 | list/报告含 per-slot cost_cny_estimate | `test_variant_stale_cost.py:213-214` |
| 8 | 夹具 pick 非 1 号槽 | `test_variant_pick_abandon.py:212,224,405`（slot_index==2 多处） |
| 9 | pick 后工作正文与 content_ref 一致；diff 代理 | `test_variant_pick_abandon.py:412,553` |
| 10 | 无 branch / 空桩 / continue / review 注册；版本 0.5.0 | review 红线核查（task 233）+ `git diff` 无 pyproject 触碰 |
| 11 | ruff / pytest / M0–M2 回归 | §7 命令输出 + 全量回归（本任务终验） |

## 完成总结

**状态**：DONE（2026-11-08）。

**声称**：M3 §6–7 代码验收 **PASS @ `594144b`**。

**证据**：

- §7 命令：`ruff check src/ tests/` 过；`tests/db/test_plan_fact_cards.py + test_dushi_lingyi_plan_facts.py + tests/plan_checks/test_plan_bible_runtime.py` 42 passed；M0–M2 CLI（workbench / canon_write / check）+ M3 CLI（variant generate / list_diff / pick_abandon / stale_cost）65 passed。
- 全量 `pytest tests/`（不带 PYTHONUTF8，task 235 修复后）：**3532 passed 零失败**。
- §6 清单 11 条证据映射见上表（均现有测试锁死，无需新代码）。

**边界**：不声称 V1.0 完成；不 bump `0.5.0`；S4/S5/S7 产品周期统计不挡代码验收（§6 原文）；真实模型冒烟另开维护者任务（§7 原文）。

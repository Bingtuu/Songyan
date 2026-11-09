# 243 · M4 §6–7 代码验收声称

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-09） |
| 关联 | [tech-m4.md](../docs/tech-m4.md) §6 验收清单（8 条）+ §7 验证命令；owner 2026-11-09 拍板声称（M4 编码 goal loop 闭环后「更新相关文档，提交并 push」） |
| 预估 | 文档切片（声称 + 证据指针；无代码改动） |

## 范围

- [x] 对照 tech-m4 §6 清单 8 条逐条指认证据（测试 / 任务文档；实跑数在 task 242 完成总结）
- [x] STATUS / HANDOFF 写「M4 §6–7 代码验收 PASS」及证据 tip
- [x] 不声称 V1.0 完成；不 bump；真实模型冒烟仍另开维护者任务（§6 原文）

## 验收标准

- [x] §6 清单 8 条每条有证据指针。
- [x] §7 命令输出全绿（文档层偏差已记录：§7 的 `tests/cli/test_chapter_continue.py` 已拆为五个 `test_chapter_continue_*` 文件，以实际文件名跑，task 242 完成总结注明）。
- [x] STATUS 一眼进度表「M4 §6–7 代码验收」行转 PASS。

## §6 清单证据映射（8 条）

| # | 条目 | 证据 |
|---|------|------|
| 1 | W2 短环 3 章走通、全程 `plan_*` approved 零变化 | `tests/cli/test_chapter_w2_loop.py`（task 242 新增；import replay 自动 chapter accepted 属历史路径，不在此口径否定面——B3 分列句） |
| 2 | `chapter accept` 干净（结算库零新行） | `tests/services/test_chapter_accept.py` 九表零新行断言（task 239） |
| 3 | 无审不连跑（exit 2 提示；`--count N` 逐章停闸） | `test_chapter_continue_gates.py` / `test_chapter_continue_count_loop.py`（task 240） |
| 4 | `review` 只读（相关表行数不变、approved 不变、不调 `merge_reviews`） | `test_review_report.py` 12 表行数不变 + merge_reviews 未调用断言（task 241） |
| 5 | `status` 露出 ContextEmergency 次数 / 最近触发章 | `test_status_command.py` emergency 三字段（task 238） |
| 6 | `today` 可作答（chapter_progress 段 + M4 `_NEXT` 文案） | task 238 `chapter_progress` 段 + task 242 `_NEXT` 两测试文件锁死 |
| 7 | exit 码表（B11）逐项 + `--require-plan` 拒绝路径 | 步 3/4 CLI 测试逐项（task 240/241） |
| 8 | ruff / 本里程碑测试 / M0–M3 回归 | §7 实跑数见 task 242 完成总结；全量终验 3593 passed 零失败 |

## 完成总结

**状态**：DONE（2026-11-09）。

**声称**：M4 §6–7 代码验收 **PASS @ `e5a33bd`**（M4 步 1–5 全部落地：238 章进度视图+status / 239 chapter accept / 240 chapter continue / 241 review 只读共审 / 242 收口）。

**证据**：

- §7 命令实跑数（task 242 完成总结）：ruff 全过；`tests/db` + `tests/plan_checks` 106 passed；M4 CLI 面 79 passed（含步 5）；全量 `python -X utf8 -m pytest tests/ -q` 终验 **3593 passed 零失败**。
- §6 清单 8 条证据映射见上表（均现有测试锁死，无需新代码）。
- 文档层偏差（记录不回改）：tech-m4 §7 引用已拆分的 `tests/cli/test_chapter_continue.py`，以实际五个 `test_chapter_continue_*` 文件跑。

**边界**：不声称 V1.0 完成；不 bump `0.5.0`；S 指标产品周期统计不挡代码验收（§6 原文）；真实模型冒烟另开维护者任务（§6 原文）；M4 之后事项（`chapter status` / `review --deep` / 导入后再续写验收）属「以后」清单，需 owner 新授权立项（tech-m4 §9）。

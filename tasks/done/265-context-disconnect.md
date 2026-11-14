# 265 · Context 断链修复（W2 定向注入 + 质量小项）— DONE

| 项 | 内容 |
|---|---|
| 状态 | **DONE**（2026-11-15；代码 @ `43eca48`） |
| 关联 | 评估文档 `docs/experiments/265-context-disconnect-eval.md`；dogfood 证据 `.tmp/dogfood-G-urban-horror-末班电梯-230946/frictions.txt` F1–F12 |
| 费用 | dogfood 复测 1 次调用 ¥0.0245 |

## 交付内容

- **S1 故事定向注入（C2/C3/C4）**：writer 工艺卡 1.1.1 → **1.1.2**（1.2.0 版本号已被多场景结构门 `writer.py strict_scenes` 预留，避让），新增三个版面变量——`故事定向`（story_brief：书名/核心冲突/主线梗概/主题/预期结局/主角+背景/核心钩子/当前弧目标/开放线索，来自 story_outlines + projects + arc_plans + plot_threads）、`角色名册`（character_roster：主角背景全量、其余裁剪 200 字）、`世界观设定`（world_setting 软引用终于有渲染分支，此前组装后被丢弃）。组装点：`workflows/_helpers.assemble_context_package`；token 计入 `_estimate_package`。
- **S2 空定向提醒**：`chapter continue` 在 chapter_goal 缺失（B12 兜底）+ brief 空 + plan_bible 空 + story_brief 空时，输出可见提醒（JSON 新增 `orientation_notice` 字段）。不阻断、不改 B12。
- **S3 project 钩子编辑面（C5）**：`storyline edit outline --core-hook / --protagonist-background` 与大纲 upsert 同事务同步 `projects` 行。
- **S4 抽卡字数门（F9）**：`variant generate` 产出通过拒写判定但低于校准字数下限（ch1–3 为 0.9×目标）→ `quality_flag=short`（不重试；`variant pick` 拒选打标槽）；CLI 原因文案「低于本章字数下限」。
- **S5 --title 回显（F3）**：`create-project --title` 成功回显打印应用后书名。

## 验收证据

- 新增测试 18 个（`tests/test_story_orientation_injection.py` 6 / `tests/test_story_orientation_assembly.py` 3 / `tests/cli/test_chapter_continue_orientation.py` 3 / storyline_cli +2 / variant quality gate +1 / create_project_title +1 / draft lock 更新）；既有 GOOD 夹具放大到过字数门。
- **dogfood 复测**（`.tmp/dogfood-265-末班电梯-003233/`，全新临时库）：urban 模板 + 恐怖 storyline **全走正规 CLI**（零 SQL、零 canon 预置）→ `chapter continue --chapter 1` 生成 2726 字 ¥0.0245，恐怖要素全命中（零点十三分/13A/庆安大厦/电梯/保安/监控），职场要素零泄漏；`--title` 回显正确。
- 全量回归 3663 passed / 2 skipped / 1 xpassed；tests/cli 339 全绿；ruff 零告警。

## 未做（留观察，勿口头开工）

- F1/F2（无 horror/empty 模板；characters 表无编辑 CLI）——产品面缺口，需 owner 立项。
- W2 自动调 goal_planner/creative_director（选项 A）——与 B12 冲突，需 owner 产品决定。
- 字数门只覆盖 variant generate 路径；`chapter continue` 直出路径仍无硬门（校准文案在 prompt 内）。

# Task 172：测试计划与合并到 main 门槛值

> 本文件记录 `task/173-project-templates` 分支（已重新编号为 Task 172）在合并回 `main` 之前需要完成的验证项与判定门槛。
>
> - 实施报告：`tasks/172-project-template-plugin-DONE.md`
> - 设计计划：`docs/superpowers/plans/2026-07-13-project-template-plugin-plan.md`

---

## 一、测试目标

1. 验证 `ProjectTemplate` 模型、加载器、初始化器在全部 7 个体裁 + 1 个变体上行为一致。
2. 验证 CLI `--template` 与 harness `TEMPLATE_ID` 集成不会破坏原有交互式路径。
3. 验证 `scripts/run_172_short_window.py` 能在真实 LLM 调用下跑通至少代表性体裁的 Ch1–Ch3。
4. 保证合并后 `main` 的既有功能（Task 171/172 harness、V7 质量门）不回归。

---

## 二、测试计划

### P0：静态与单元测试（必须全部通过，阻塞合并）

| # | 验证项 | 命令 | 通过标准 |
|---|--------|------|----------|
| P0-1 | 模板模型/加载器/初始化器/继承测试 | `python -m pytest tests/test_project_template_models.py tests/test_project_template_loader.py tests/test_project_template_initializer.py tests/test_project_template_inheritance.py -q` | 20 passed |
| P0-2 | 全量回归（排除性能测试） | `python -m pytest tests/ -q -m "not performance"` | ≥2434 passed, 2 skipped, 210 deselected，无新增失败 |
| P0-3 | Lint / 类型检查 | `ruff check src/songyan/project_templates/ tests/test_project_template_*.py scripts/run_172_short_window.py src/songyan/cli/main.py` <br> `mypy src/songyan/project_templates/ scripts/run_172_short_window.py` | 无新增告警 |

### P1：集成冒烟测试（必须全部通过，阻塞合并）

这些测试不调用 LLM，只验证模板加载、DB 初始化、CLI/harness 接线正确。

| # | 验证项 | 命令 | 通过标准 |
|---|--------|------|----------|
| P1-1 | 7 个体裁模板均可加载并携带大纲 | `python -c "from songyan.project_templates import ProjectTemplateLoader; loader=ProjectTemplateLoader(); [print(tid, loader.load(tid).has_outline) for tid in ['scifi','xuanhuan','wuxia','urban','urban_fantasy','post_apocalyptic','mystery_noir']]"` | 全部 `True` |
| P1-2 | 变体模板继承父模板并覆盖成功 | `python -c "from songyan.project_templates import ProjectTemplateLoader; t=ProjectTemplateLoader().load('xuanhuan/cultivation'); print(t.project_setting.title, t.project_setting.protagonist_name, t.seed.characters[0].name, t.has_outline)"` | 输出 `万道独尊 韩立 韩立 True` |
| P1-3 | CLI `--template` 为每个体裁创建项目 | `songyan create-project --template <genre_id>`（对 7 个体裁分别执行） | 不抛异常，输出项目 ID |
| P1-4 | Harness `--init` 为每个体裁创建项目 | `$env:TEMPLATE_ID="<genre_id>"; python scripts/run_171_ch200.py --init`（对 7 个体裁分别执行） | 成功创建 project_id 并导入 arcs/threads |
| P1-5 | 短章脚本 help / import 正常 | `python scripts/run_172_short_window.py --help` | 正常显示参数 |

### P2：LLM 短章验证（推荐执行，预算受限时可降级）

这是验证模板在真实生成链路中是否有效的最终证据。

| # | 验证项 | 命令 | 通过标准 |
|---|--------|------|----------|
| P2-1 | 至少 2 个体裁跑 Ch1–Ch3 | `python scripts/run_172_short_window.py --templates scifi xuanhuan --end 3` | 每个体裁 `completed=[1,2,3]`、`failed=[]`、`status=completed`、`t9_issue_count=0`、`word_count_avg` 在 2500–3500 之间 |
| P2-2 | 全部 7 个体裁至少跑 Ch1 | `python scripts/run_172_short_window.py --end 1` | 每个体裁 `completed=[1]`、`failed=[]`、`status=completed`、`t9_issue_count=0` |
| P2-3 | 变体模板短章验证 | `python scripts/run_172_short_window.py --templates xuanhuan/cultivation --end 3` | 与 P2-1 同标准 |

**预算降级策略**：若 P2-1 无法全跑，优先保证 P2-2（7 个体裁各 1 章）通过；若仍受限，至少跑 `scifi` + `xuanhuan` 两个差异最大的体裁。

### P3：回归与边界测试（必须全部通过，阻塞合并）

| # | 验证项 | 命令 / 步骤 | 通过标准 |
|---|--------|-------------|----------|
| P3-1 | 未知模板报错友好 | `python -c "from songyan.project_templates import ProjectTemplateLoader; ProjectTemplateLoader().load('not_exists')"` | 抛出 `ProjectTemplateNotFoundError` 并列出可用模板 |
| P3-2 | 循环继承被检测 | `python -m pytest tests/test_project_template_inheritance.py tests/test_project_template_loader.py -q -k circular` | 2 passed |
| P3-3 | 无模板时 CLI 交互式路径仍可用 | `songyan create-project`（不带 `--template`） | 进入交互式选择，正常创建项目 |
| P3-4 | `run_171_ch200.py` 默认行为不变 | `python scripts/run_171_ch200.py --init` | 使用默认 `TEMPLATE_ID=scifi`，成功创建项目 |

---

## 三、合并到 main 的门槛值

必须同时满足以下全部条件，才能执行合并（Option 1：本地合并 或 Option 2：PR）：

- [ ] P0-1 ~ P0-3 全部通过。
- [ ] P1-1 ~ P1-5 全部通过。
- [ ] P3-1 ~ P3-4 全部通过。
- [ ] P2 至少完成降级策略（7 个体裁各 Ch1，或至少 scifi + xuanhuan 的 Ch1–Ch3）。
- [ ] 合并后在工作树执行 `python -m pytest tests/ -q -m "not performance"` 仍通过。
- [ ] `ruff check src/ tests/` 不新增告警（允许既有的 13 个 pre-existing 警告）。
- [ ] `tasks/V7-README.md` 与 `docs/STATUS.md` 中的 Task 172 状态保持准确。
- [ ] 无未解决的 `BLOCKER`/`CRITICAL` 评审意见。

---

## 四、建议的合并流程

1. 在当前工作树完成上述 P0–P3 验证。
2. 切换到 `main` 并拉取最新代码：
   ```bash
   git checkout main
   git pull
   ```
3. 合并 feature 分支：
   ```bash
   git merge task/173-project-templates
   ```
4. 在合并后的 `main` 重新执行 P0-2 全量回归。
5. 通过后再删除工作树与分支：
   ```bash
   git worktree remove .worktrees/task-173-project-templates
   git branch -d task/173-project-templates
   ```

---

## 五、已知限制（不阻塞合并）

- `ProjectInitializer.from_template()` 按现有 repository 模式顺序写入 DB，非原子事务；这是当前 repository 层的已知限制，与 Task 172 范围无关。
- `scripts/run_172_short_window.py` 全量运行消耗 API 预算；合并前只需完成降级策略即可。

---

## 六、执行记录（2026-07-14）

- [x] P0-1：20 passed
- [x] P0-2：2441 passed, 2 skipped, 210 deselected
- [x] P0-3：ruff / mypy 无新增告警
- [x] P1-1：7 个体裁模板加载 + 携带大纲全部 True
- [x] P1-2：变体模板 `xuanhuan/cultivation` 加载输出 `万道独尊 韩立 韩立 True`
- [x] P1-3：CLI `--template` 为 7 个体裁均成功创建项目
- [x] P1-4：Harness `--init` 为 7 个体裁均成功创建项目
- [x] P1-5：`run_172_short_window.py --help` 正常
- [ ] P2-1：`scifi + xuanhuan` Ch1–Ch3 LLM 短章验证正在后台运行（`bash-nhrurdrk`）
- [ ] P2-2 / P2-3：未执行
- [x] P3-1：未知模板报错友好
- [x] P3-2：循环继承检测 2 passed
- [x] P3-3：无模板交互式 CLI 在 UTF-8 终端正常创建项目
- [x] P3-4：`run_171_ch200.py --init` 默认 `scifi` 行为不变

### 合并前修复

1. `src/songyan/project_templates/initializer.py`：从模板导入大纲时，将 `thread_id` 前缀化为 `{project_id}-{original_thread_id}`，避免同一数据库中多项目线索 ID 冲突；同步更新 `arc_plans` 中的 `threads_to_open` / `threads_to_resolve` 引用。
2. `src/songyan/cli/main.py`：将项目创建成功提示中的 Unicode 对勾 `✓` 替换为 ASCII `[OK]`，避免 Windows GBK 控制台编码错误导致 CLI 退出码非零。

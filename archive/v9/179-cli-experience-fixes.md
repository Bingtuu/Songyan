# Task 179: CLI 体验修复

> **阶段**: V9.2 交付与发布  
> **类型**: CLI 可用性与文档一致性  
> **优先级**: P1（V9-README 审计 P1：CLI 三坑）  
> **依赖**: 177 export 已完成；178 wheel 打包与资源加载已完成；176 wrapper 可用于防卡测试  
> **状态**: ✅ 完成（DONE: `archive/v9/179-cli-experience-fixes-DONE.md`）
> **来源**: `tasks/V9-README.md` Task 179 行；V9 生产就绪度审计 P1

---

## 任务边界

本任务只修 V9-README 明确列出的三个 CLI 体验缺口：

1. `songyan run` 成功结束后必须回显 `run_id`，让用户能直接复制到 `songyan report --run-id <id>` 或日志定位流程。
2. `songyan run --mode-id` 未显式传入时，默认使用项目库中 `projects.mode_id`，而不是总是使用 Click 默认值 `webnovel`。
3. README 的 CLI 命令表补齐 `songyan index`，并让 `run` / `report` / `export` / `index` 的关键参数描述与当前 Click 实现一致。

不做：

- 不新增 CLI 命令，不改命令分组结构。
- 不改生成 workflow、Agent 节点、状态结算或事实写入路径。
- 不修 `tests/cli/test_cli.py` 之外的历史 CLI 问题；CI 与 `tests/cli` 默认忽略策略归 Task 181。
- 不做 `songyan doctor` 环境自检；该项归 Task 180。

## 当前代码事实（2026-07-19 扫描）

- `src/songyan/cli/main.py` 的 `run` 命令当前 `@click.option("--mode-id", default="webnovel", ...)`，因此用户不传 `--mode-id` 时无法区分“未传”与“主动选 webnovel”。
- `run_project_pipeline(...)` 返回 `ProjectRunResult`，CLI 当前只输出成功章数、失败章号与耗时，没有输出 `result.run_id`。
- `ProjectRepository` 已可读取项目；`ProjectSetting` 含 `mode_id`，`create-project` 与 `list-projects` 已展示该字段。
- `src/songyan/cli/commands/index.py` 已注册 `songyan index --project-id --chapters --rebuild`，但 README CLI 表未列出。
- `tests/cli/test_cli.py` 已存在 CliRunner 基础夹具，但默认测试配置仍在 `pyproject.toml` 中忽略 `tests/cli`；本任务可新增聚焦测试并直接运行，不改变全量默认忽略策略。

## 设计方案

### 1. `run_id` 输出

在 `run` 命令拿到 `ProjectRunResult` 后输出：

```text
run_id: <result.run_id>
```

位置放在完成摘要之后、耗时之前或之后均可，但必须是稳定可 grep 的英文键，便于脚本解析。

### 2. 默认 mode 读取项目值

把 `--mode-id` 的 Click 默认值改为 `None`，语义变为：

- 用户显式传 `--mode-id <mode>`：使用显式值，维持当前覆盖能力。
- 用户不传 `--mode-id`：从 SQLite 读取 `projects.mode_id`。
- 项目不存在或 `mode_id` 为空：报 `ClickException`，提示用户指定 `--mode-id` 或检查 project id。

读取项目值必须通过 `ProjectRepository`，不能直接开 SQLite connection。

实现建议新增小型 async helper（如 `_resolve_run_mode_id(project_id, explicit_mode_id)`）：

- helper 内部处理“显式值优先”和 DB fallback；
- Click 命令只调用一次 `asyncio.run(...)` 获取最终 mode；
- 测试可直接 monkeypatch helper 或 `ProjectRepository.get`，避免为 CLI 行为测试搭真实生成链路。

### 3. README CLI 表同步

补齐 `songyan index`，并更新 `songyan run` 的参数描述：

- `--mode-id` 是可选覆盖项，默认回读项目 mode。
- `--run-id` 与 `--resume` 的关系：`--run-id` 优先。
- `--gate-mode`、`--on-failure`、`--rag-mode` / `--skip-rag` 只做简洁列出，不展开成长文档。

## TDD 测试计划

新增或扩展 `tests/cli/test_cli.py`：

1. `run` 成功后输出 `run_id`：
   - monkeypatch `run_project_pipeline` 返回固定 `ProjectRunResult`。
   - monkeypatch mode 解析函数，避免真实 LLM。
   - 断言输出包含 `run_id: run-179`.
2. `run` 不传 `--mode-id` 时读取项目 mode：
   - monkeypatch `_resolve_run_mode_id` 或 `ProjectRepository.get` 返回 `ProjectSetting(mode_id="webnovel_intense", ...)`。
   - monkeypatch `run_project_pipeline` 记录入参。
   - 断言传入 `mode_id == "webnovel_intense"`。
3. `run --mode-id hybrid` 显式覆盖项目 mode：
   - 项目返回 `webnovel_intense`。
   - 断言传入 `mode_id == "hybrid"`。
4. `run` 在项目不存在时失败：
   - `_resolve_run_mode_id` 抛出 `ClickException` 或 `ProjectRepository.get` 返回 `None`。
   - 断言 exit 非 0，错误信息说明无法读取项目 mode。
5. `index --help` 注册与 README 表一致：
   - `runner.invoke(cli, ["index", "--help"])` 成功，包含 `--project-id`、`--chapters`、`--rebuild`。

测试必须避免真实 LLM、真实 embedding 与长跑。

## 验证命令

```powershell
python -m pytest tests/test_130_gate_mode.py tests/cli/test_cli.py::TestRunCommandExperience tests/cli/test_cli.py::TestCommandRegistration::test_index_help -q
python -m pytest tests/ -q
ruff check src/ tests/
```

若 Windows 下全量 pytest 卡住，使用 Task 176 wrapper：

```powershell
powershell -NoProfile -File scripts/run_with_timeout.ps1 -TimeoutSec 1800 -DetectPytestSummary -- python -m pytest tests/ -q
```

## 执行记录（2026-07-19）

- `songyan run --mode-id` 默认值从 `webnovel` 改为 `None`，未显式传入时通过 `_resolve_run_mode_id()` 从 `ProjectRepository.get(project_id)` 读取 `projects.mode_id`。
- 显式传入 `--mode-id <mode>` 时保持最高优先级，不读取项目默认 mode。
- 项目不存在或无法读取 `mode_id` 时抛出可读 `ClickException`，不再静默回退 `webnovel`。
- `songyan run` 成功后输出稳定行：`run_id: <id>`，便于 `songyan report --run-id <id>` 和日志定位。
- README CLI 表补充 `songyan index`，并同步 `run` 的 `--mode-id`、`--run-id`、`--resume`、`--gate-mode`、`--on-failure`、RAG 参数口径。
- `tests/test_130_gate_mode.py` 的 gate-mode 成功路径显式传入 `--mode-id webnovel`，避免把 Task 179 的项目 mode fallback 混入 gate 测试意图。
- Code review 使用 `bits-code-guard` 对 `src/songyan/cli/main.py` 当前 diff 做通用检测，未发现 P0/P1/P2 缺陷；报告生成于 `.tmp/code_guard_179/report.html` / `.tmp/code_guard_179/report.md`。

### 验证结果（2026-07-19）

| 项 | 结果 |
|---|---|
| Task 179 聚焦 CLI 测试 | `python -m pytest tests/test_130_gate_mode.py tests/cli/test_cli.py::TestRunCommandExperience tests/cli/test_cli.py::TestCommandRegistration::test_index_help -q` → **12 passed** |
| Ruff | `ruff check src/ tests/` → **All checks passed** |
| 默认全量 pytest | `powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 1800 -DetectPytestSummary -- python -m pytest tests/ -q` → **2903 passed, 2 skipped, 1 xfailed, 7 warnings**；`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| Code review | `bits-code-guard` diff-only review → **0 P0/P1/P2 findings** |

> 说明：`tests/cli/test_cli.py` 全文件仍含 4 个既有 `create-project` 输出解析失败，属于 V9 Task 181 “CI 上线与测试清零”范围；本 Task 179 只新增并运行三坑相关聚焦测试。

## 验收判据

- `songyan run` 成功输出含稳定 `run_id: ...` 行。
- `songyan run` 未传 `--mode-id` 时使用 DB 中的项目 mode；显式传入时仍可覆盖。
- 项目不存在时给出可读 CLI 错误，而不是静默回退 `webnovel`。
- `songyan index` 在 README CLI 表中可见，参数描述与当前实现一致。
- 聚焦 CLI 测试通过，全量默认测试与 Ruff 通过。
- `tasks/V9-README.md`、`docs/STATUS.md`、`README.md`、`docs/INDEX.md` 同步 Task 179 状态与证据。

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| `ProjectRepository.get` 是 async，Click 命令中处理不当 | CLI 测试出现 event loop/runtime error | 用 `asyncio.run()` 封装一个小型 async helper，与现有 CLI 风格保持一致 |
| tests/cli 既有失败干扰本任务 | 聚焦测试出现与本任务无关的旧失败 | 先定位；只修与 179 三坑直接相关的问题，Task 181 再清 CLI 全量历史失败 |
| 默认 mode 改动影响 resume | resume 测试失败或入参不一致 | `--run-id` / `--resume` 只影响 run 记录复用，不改变 mode 解析优先级；mode 仍按“显式 CLI > 项目默认” |
| README 过度展开 | README CLI 表变成长篇参考手册 | 保持表格简洁，详细 help 仍以 `songyan <command> --help` 为准 |

## Out of Scope

- CI 配置、`tests/cli` 默认忽略策略、badge 自动化。
- `songyan doctor`。
- `profile show/diff/upsert`。
- 五门工具收编。
- 任意真实 LLM 生成回归；本 task 只修 CLI 包装行为，scifi end10 守护不强制执行。

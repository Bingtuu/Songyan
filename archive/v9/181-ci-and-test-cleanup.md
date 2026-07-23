# Task 181: CI 上线与测试清零

> **阶段**: V9.2 交付与发布
> **类型**: CI / 测试治理 / 发布基础设施
> **优先级**: P1（V9 A6：CI 上线；`tests/cli` 不再默认跳过或由 CI 单独覆盖；4 个既有失败修复）
> **依赖**: 173-180 已完成；176 wrapper 可用于本地防卡验证；179/180 已新增 CLI 聚焦测试
> **状态**: ✅ 完成（DONE: `archive/v9/181-ci-and-test-cleanup-DONE.md`）
> **来源**: `tasks/V9-README.md` Task 181 行；V9 生产就绪度审计 P1

---

## 任务边界

本任务完成 V9.2 的交付发布收口：

1. 上线 GitHub Actions CI，覆盖 ruff、mypy 与 pytest 默认测试。
2. 修复 `tests/cli` 当前 4 个既有失败，或把其纳入 CI 单独覆盖并全绿。
3. 明确本地默认测试与 CI 测试口径差异，避免“本地绿但 CI 漏跑”的治理缝隙。
4. README tests badge 改为稳定机制，不再手工更新通过数。

不做：

- 不做正式 release、版本 bump 或 PyPI 发布。
- 不做 profile CLI、五门工具收编、urban 标定。
- 不改业务 workflow / Agent 逻辑。

## 当前事实（2026-07-20 扫描）

- 仓库当前无 `.github/workflows/`。
- `pyproject.toml` 默认 `addopts = "--ignore=tests/evals --ignore=tests/cli"`；因此 `python -m pytest tests/ -q` 不覆盖 CLI 测试目录。
- Task 179/180 已新增 CLI 聚焦测试，但因 `tests/cli` 被默认忽略，全量默认测试不会自动跑到这些用例。
- 当前 `python -m pytest tests/cli -q` 结果：**4 failed, 31 passed**。
- 4 个失败均在 `tests/cli/test_cli.py::TestCreateProject`，根因是测试的 `_extract_project_id()` 只匹配 `line.startswith("✓ 项目已创建:")`，而实际输出行前有 Click/终端交互残留空白；功能本身已创建项目成功。
- 当前 `mypy src/` 结果：**27 errors / 9 files**，主要集中在 Task 178 后 `Traversable` 类型声明与 `exists()/parent` API 不匹配、`logging_setup` processor 类型、少量 Literal/annotation。

## 设计方案

### 1. 修复 CLI 测试既有失败

最小修复：

- 将 `_extract_project_id()` 改为对每行 `strip()` 后匹配 `✓ 项目已创建:`。
- 若仍有失败，再按实际输出修正测试，不改变 `create-project` 用户输出格式。
- 保持 Task 179/180 新增 CLI 测试在 `tests/cli` 内。

### 2. CI workflow

新增 `.github/workflows/ci.yml`：

```yaml
name: CI
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup-python 3.11
      - pip install -e ".[dev]"
      - ruff check src/ tests/
      - mypy src/
      - python -m pytest tests/ -q
      - python -m pytest tests/cli -q
```

说明：

- CI 单独跑 `tests/cli`，不必在本任务立即修改 `pyproject.toml` 默认忽略策略；本地默认全量维持历史耗时与口径。
- 若 CI 环境缺少重依赖或模型下载导致默认测试不稳定，可拆成 `unit` 与 `cli` 两个 job，但不能漏掉 `tests/cli`。
- 不在 CI 中跑真实 LLM 生成。

### 3. README badge 机制

当前 README 手写 `tests-2903 passed` 容易漂移。本任务改为稳定说明：

- 优先使用 GitHub Actions badge：`![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)`。
- 如仓库 URL 不稳定，则改为静态 “CI: GitHub Actions” badge，不再写具体 passed 数。
- README “测试”行改为说明默认 pytest 与 CLI pytest 分开跑。

### 4. 文档同步

- `tasks/V9-README.md`：Task 181 翻正，A6 标为已闭环。
- `docs/STATUS.md`：记录 CI/CLI 测试证据。
- `README.md`：badge 与开发验证命令同步。
- `docs/INDEX.md`：加入 Task 181 DONE。

## TDD 测试计划

1. 先跑 `python -m pytest tests/cli -q` 复现 4 fail。
2. 修 `_extract_project_id()` 后跑 `python -m pytest tests/cli -q`，预期全绿。
3. 跑默认全量 `python -m pytest tests/ -q`，确认默认口径不回退。
4. 跑 `mypy src/`，预期 0 errors。
5. 跑 `ruff check src/ tests/`。
6. 可选检查 CI YAML 语法：至少确认文件存在、包含 `mypy src/`、`python -m pytest tests/cli -q` 和 `ruff check src/ tests/`。

## 验证命令

```powershell
python -m pytest tests/cli -q
mypy src/
powershell -NoProfile -File scripts/run_with_timeout.ps1 -TimeoutSec 1800 -DetectPytestSummary -- python -m pytest tests/ -q
ruff check src/ tests/
```

## 执行记录（2026-07-20）

- 修复 `tests/cli/test_cli.py` 的 `_extract_project_id()`：改为从完整输出中用正则提取 `项目已创建: <32hex>`，解决 Click 交互提示残留导致的 4 个 create-project 测试失败。
- 修复 `mypy src/` 27 个错误：
  - `Traversable.exists()/parent` 类型问题改为 `is_dir()/is_file()`、显式目录变量、`as_file()`；
  - `ProjectTemplateLoader` zip-backed `outline.json` 通过 `as_file()` 转真实路径；
  - `logging_setup` 对 structlog processor 列表做局部 `cast(Any, ...)`；
  - `continuity_health` severity、`llm.client` cost_source、`lifecycle_cleaners` 返回类型补齐。
- 新增 `.github/workflows/ci.yml`：CI 覆盖 `ruff check src/ tests/`、`mypy src/`、默认 `python -m pytest tests/ -q`、`python -m pytest tests/cli -q`。
- README 移除手写 passed 数 badge，改为 GitHub Actions workflow badge；开发验证命令补 `tests/cli`。
- Code review 使用 `bits-code-guard` 分 3 组审查，发现 1 个 P2（zip-backed `outline.json` 未 `as_file()`），已修复并补 `test_load_zip_backed_directory_template_outline` 回归测试；报告生成于 `.tmp/code_guard_181/report.html` / `.tmp/code_guard_181/report.md`。

### 验证结果（2026-07-20）

| 项 | 结果 |
|---|---|
| CLI 测试 | `python -m pytest tests/cli -q` → **35 passed** |
| mypy | `mypy src/` → **Success: no issues found in 172 source files** |
| Ruff | `ruff check src/ tests/` → **All checks passed** |
| 默认全量 pytest | `powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 1800 -DetectPytestSummary -- python -m pytest tests/ -q` → **2904 passed, 2 skipped, 1 xfailed, 7 warnings**；`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| Code review | `bits-code-guard` diff-only grouped review → 1 P2 found and fixed |

## 验收判据

- `tests/cli` 全绿，当前 4 个既有失败清零。
- `mypy src/` 全绿。
- 默认全量 pytest + ruff 仍全绿。
- `.github/workflows/ci.yml` 存在并覆盖 ruff、mypy、默认 tests 与 `tests/cli`。
- README 不再使用手工 passed 数 badge。
- V9 A6 在 `tasks/V9-README.md` 中翻正。

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| CI 环境下载重依赖过慢 | CI 默认测试卡在 embedding/model 下载 | 先维持本地默认测试证据；CI job 可加缓存或拆分，但不得移除 CLI 覆盖 |
| `tests/cli` 修复扩大到业务输出改动 | 为了测试改用户可见输出 | 优先修测试解析；只有确认为 CLI 输出 bug 时才改生产代码 |
| README badge URL 不确定 | 不知道 GitHub owner/repo | 使用 workflow 文件名相对稳定的 actions badge，或退回非数字静态 CI badge |
| pyproject 默认忽略策略争议 | 移除 `--ignore=tests/cli` 导致本地默认测试口径变化 | 本任务允许 CI 单独覆盖 CLI；是否改默认忽略必须在文档中显式说明 |

## Out of Scope

- 真实 LLM integration CI。
- 发布流水线、版本号 bump、PyPI。
- Task 182 五门工具收编。

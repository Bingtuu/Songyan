# Songyan Release Checklist

> 开源发布总验收清单。正式发布前按本文件逐项确认；不满足硬门槛时只能发 preview 或 release candidate。

## 当前结论

当前代码已具备面向外部技术用户的 technical preview / release-candidate 条件。正式开源可用版本发布前，维护者仍应在目标 release commit 上重新执行本清单，并确认真实 LLM Ch1-3 smoke 的成本和结果可接受。

## 硬门槛

| 项 | 标准 | 状态 |
|----|------|:----:|
| 版本号 | `pyproject.toml` 版本与 CHANGELOG release 条目一致 | PASS |
| License | 仓库根目录存在 AGPL-3.0 `LICENSE` | PASS |
| README | 外部用户不读历史任务也能理解定位、安装、Quickstart 和限制 | PASS |
| Quickstart | 文档覆盖 `doctor -> create-project -> run -> report -> export` | PASS |
| Doctor | 缺 key、DB/schema、资源、日志、预算等有诊断和恢复建议 | PASS |
| Backup / restore | 项目资产可备份、恢复并校验 schema | PASS |
| Run bundle | 可生成脱敏诊断包用于复现问题 | PASS |
| Profile 安全 | validate、dry-run、history、rollback 可用 | PASS |
| Wheel smoke | wheel 构建、安装后非仓库 cwd 资源检查、建项、导出通过 | PASS |
| CI | ruff、runtime mypy、pytest、CLI pytest、wheel smoke 已接入 | PASS |
| Issue 模板 | 要求最小复现、doctor 输出和脱敏诊断信息 | PASS |
| 最小复现指南 | 用户可按文档提供可复现问题 | PASS |

## 本地验证命令

```powershell
python -m pip wheel . --no-deps -w .tmp/task215-wheel
python -m pytest tests/cli -q
ruff check src/ tests/
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 900 -- python -m pytest tests/ -q
```

## Wheel / 非仓库 cwd smoke

维护者可按以下方式复验 wheel：

```powershell
python -m pip wheel . --no-deps -w .tmp/task215-wheel
python -m venv --system-site-packages .tmp/task215-venv
.\.tmp\task215-venv\Scripts\python.exe -m pip install --no-deps --force-reinstall .tmp\task215-wheel\songyan-*.whl

$smoke = Join-Path $env:TEMP "songyan-release-smoke"
Remove-Item $smoke -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $smoke | Out-Null
Push-Location $smoke

$env:DATABASE_URL = "sqlite:///$smoke\release-smoke.db"
$env:CHECKPOINTER_MODE = "memory"
$env:LLM_API_KEY = "dummy-key-for-doctor"

songyan --help
songyan doctor --json --init-db
songyan create-project --template scifi
songyan profile validate --genre scifi --json

Pop-Location
```

`export` 需要 accepted 章节。正式 release smoke 可以用真实 Ch1-3 accepted 结果；无真实 LLM 凭证时，可用测试 DB 中构造的 accepted 章节验证 wheel 版导出路径，证据应保存在 release notes、CI artifact 或本地忽略目录中。

## 真实 LLM Smoke

正式发布前建议执行：

```powershell
songyan doctor --json --init-db
songyan create-project --template scifi
songyan run --project-id <project_id> --chapters 1-3 --auto-confirm
songyan report --run-id <run_id>
songyan bundle-run --run-id <run_id> --output bundles/
songyan export --project-id <project_id> --chapters 1-3 --format md --output exports/
```

验收口径：

- `run` exit code 为 0。
- Ch1-3 均 accepted。
- `report` 成功生成。
- `bundle-run` 不包含 `.env`、API key、日志正文或书稿正文。
- `export` 至少导出一个 Markdown 或 txt 文件。

如果没有真实 LLM 凭证或维护者不希望消耗预算，该项不能伪造为真实运行；应在 release notes 中标注为未执行或使用替代 smoke。

## 发布前人工检查

- 更新 `CHANGELOG.md` release 日期和版本。
- 确认 `pyproject.toml` 版本号。
- 确认 CI 通过。
- 确认 `src/songyan/evals/` 仍保持 research / report-only 边界；该目录不属于 runtime mypy release gate。
- 确认 `docs/STATUS.md` 与 README 状态一致。
- 确认没有提交 `.env`、DB、日志、bundle、backup 或私密书稿。
- 确认 issue template 和 `docs/minimal-repro.md` 链接有效。

## 不变边界

- 不把 research / report-only signals 接入 prompt、CED 或 hard gate。
- CED 仍只统计 consistency-only、merged/source、正文证据。
- T9 仍是硬红线。
- SQLite 仍是唯一长期事实源。

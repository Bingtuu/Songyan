# Task 180: songyan doctor 环境自检

> **阶段**: V9.2 交付与发布
> **类型**: CLI 诊断工具 / 生产化地基
> **优先级**: P1（首次运行前给出可读环境诊断，减少真实 LLM 调用才暴露配置错误）
> **依赖**: 173-179 已完成；178 已保证 wheel 资源可从包内加载；179 已修复 CLI 基础体验
> **状态**: ✅ 完成（DONE: `archive/v9/180-doctor-environment-check-DONE.md`）
> **来源**: `tasks/V9-README.md` Task 180 行；V9 生产就绪度审计 P1

---

## 任务边界

本任务实现 `songyan doctor`，用于在用户首次生成前做本地环境自检：

1. `.env` / settings 基础配置可读。
2. LLM API key、base_url、model 的配置状态可诊断。
3. SQLite DB 路径可解析、目录可写、schema 可初始化或验证。
4. wheel/package runtime 资源完整：7 个 genre、4 个 creative mode、项目模板、prompt cards、literary plugins、`evals/seeds`、`schema.sql`。
5. `checkpointer_mode` 等关键运行模式值可读且在支持集合内。
6. 输出面向用户的 PASS/WARN/FAIL 摘要；若关键项失败，给出下一步修复建议。

不做：

- 不新增长跑逻辑，不调用 workflow，不生成正文。
- 默认不发真实 LLM 请求，避免 doctor 成为成本入口。
- 不实现 profile CLI；归 Task 183。
- 不修 `tests/cli` 全量历史失败；归 Task 181。

## 当前代码事实（2026-07-19 扫描）

- `Settings` 在 `src/songyan/config.py` 中通过 Pydantic Settings 读取 `.env`，关键字段包括 `llm_api_key`、`llm_base_url`、`llm_model`、`database_url`、`checkpointer_mode`、`run_cost_budget`。
- `get_db_path(settings.database_url)` 可解析 SQLite DB 路径；不支持非 SQLite URL 时抛 `ValueError`。
- `init_schema()` 会写库，不适合 doctor 默认只读检查直接调用源库；但 doctor 的“可写检查”可在 DB 父目录中创建临时探针文件，或在用户显式 `--init-db` 时才执行初始化。
- `verify_schema(conn)` 可用于已存在 DB 的 schema 完整性检查。
- Task 178 已把 runtime 资源迁入包内，doctor 可用 `importlib.resources.files()` 和现有 loader 做资源完整性检查。
- `songyan.llm.client.get_llm()` 缺 key 时会抛“LLM API Key 未配置”，但这发生在首次 LLM 调用路径；doctor 应提前暴露同类信息。

## 设计方案

### CLI 接口

新增命令：

```powershell
songyan doctor [--json] [--check-llm] [--init-db]
```

- 默认模式：本地无成本检查，只读取配置、资源与 DB 路径，不发真实网络请求。
- `--json`：输出机器可读 JSON，便于 CI 或脚本消费。
- `--check-llm`：显式 opt-in 的 LLM 连通性检查；只做最小请求或模型配置探针，必须走预算/错误保护，失败输出 WARN/FAIL 但不泄露 key。
- `--init-db`：显式允许初始化/迁移当前 `DATABASE_URL` 指向的 SQLite DB；默认不主动写业务库。

### 检查项

| ID | 检查 | 默认级别 | 失败口径 |
|---|---|---|---|
| config.env | `.env` 是否存在，settings 能否加载 | WARN | `.env` 不存在但环境变量齐全可继续；settings 加载异常为 FAIL |
| llm.key | `LLM_API_KEY` / `llm_api_key` 是否非空 | FAIL | 默认只检查存在性，不打印 key |
| llm.config | `LLM_BASE_URL` / `LLM_MODEL` / temperature 基础值 | FAIL/WARN | base_url/model 空为 FAIL；temperature 越界为 WARN/FAIL |
| db.url | `DATABASE_URL` 是否为支持的 SQLite URL | FAIL | 非 SQLite URL 报清晰提示 |
| db.path | DB 父目录存在或可创建、可写 | FAIL | 父目录不可写或路径非法 |
| db.schema | DB 已存在时 schema 是否完整 | WARN/FAIL | 缺表为 WARN，提示可运行 `songyan doctor --init-db`；连接失败为 FAIL |
| runtime.checkpointer | `checkpointer_mode` 是 `memory` 或 `sqlite` | FAIL | 非法值为 FAIL |
| resources.package | genre/mode/template/cards/plugins/seeds/schema.sql 可加载 | FAIL | 任一核心资源缺失为 FAIL；数量只用下限或核心样本断言，避免模板派生数量变化导致误报 |
| llm.connectivity | opt-in LLM 连通性 | WARN/FAIL | 仅 `--check-llm` 执行；认证失败、网络失败给可读建议 |

### 输出格式

默认文本输出：

```text
Songyan doctor

[PASS] config.env: .env loaded
[PASS] llm.key: LLM_API_KEY configured
[PASS] db.url: sqlite:///songyan.db
[WARN] db.schema: database does not exist; run songyan doctor --init-db to initialize
[PASS] resources.package: 7 genres, 4 modes, templates/cards/plugins/seeds/schema ok

Summary: 4 PASS, 1 WARN, 0 FAIL
```

规则：

- 有 FAIL 时进程 exit code = 1。
- 只有 PASS/WARN 时 exit code = 0。
- 不在 console 打印 secrets。
- JSON 输出字段固定，便于测试：

```json
{
  "status": "pass|warn|fail",
  "checks": [
    {"id": "llm.key", "status": "pass", "message": "...", "hint": "..."}
  ],
  "summary": {"pass": 1, "warn": 0, "fail": 0}
}
```

## TDD 测试计划

新增 `tests/cli/test_doctor_command.py`：

1. `doctor --help` 显示 `--json`、`--check-llm`、`--init-db`。
2. `.env` 不存在但 monkeypatch settings key 存在 → `config.env` WARN 或 PASS，不阻塞。
3. 缺 `llm_api_key` → exit code 1，输出 FAIL 且不泄露任何 key 值。
4. 非 SQLite `database_url` → exit code 1，错误提示说明仅支持 SQLite。
5. DB 父目录不可写/非法路径 → FAIL（Windows 下用不存在盘符不稳定，优先用 monkeypatch helper 返回失败）。
6. 已存在空 DB 缺 schema → WARN，提示 `--init-db`。
7. `--init-db` 对临时 DB 执行 schema 初始化，随后 schema check PASS。
8. 包资源完整检查 PASS：7 genre、4 mode、核心模板、cards、plugins、`evals/seeds`、`schema.sql`。
9. `--json` 输出合法 JSON，summary 与文本状态一致。
10. `--check-llm` 默认不执行；显式传入时调用可 monkeypatch 的 LLM probe helper，不发真实请求。
11. 非法 `checkpointer_mode` 通过 helper 层模拟，doctor 输出 FAIL。

测试必须全部使用临时目录、monkeypatch settings 和 mock LLM probe，不访问真实 API。

## 验证命令

```powershell
python -m pytest tests/cli/test_doctor_command.py -q
python -m pytest tests/ -q
ruff check src/ tests/
```

若 Windows 下全量 pytest 卡住，使用 Task 176 wrapper：

```powershell
powershell -NoProfile -File scripts/run_with_timeout.ps1 -TimeoutSec 1800 -DetectPytestSummary -- python -m pytest tests/ -q
```

## 执行记录（2026-07-20）

- 新增 `src/songyan/services/doctor_service.py`：
  - `DoctorCheck` / `DoctorReport` 结构化结果；
  - 默认只读检查 `.env`、LLM key/config、SQLite URL/path/schema、checkpointer mode、runtime package resources；
  - `--init-db` 才调用 `init_schema()`；
  - `--check-llm` 才执行 LLM client 初始化探针，默认不发真实 LLM 请求；
  - schema 检查在 `verify_schema()` 表名检查后增加关键迁移列/索引 drift 检测，避免旧库缺列被误报 complete。
- 新增 `songyan doctor [--json] [--check-llm] [--init-db]`：
  - 文本输出 PASS/WARN/FAIL；
  - `--json` 输出稳定 JSON；
  - 任一 FAIL 时 exit code = 1，仅 WARN/PASS 时 exit code = 0。
- 新增 `tests/cli/test_doctor_command.py` 12 个聚焦用例，覆盖 help、缺 key、非法 DB URL、缺 schema、`--init-db`、资源检查、JSON 输出、LLM probe opt-in、非法 checkpointer mode、schema drift。
- Code review 使用 `bits-code-guard` 对 `src/songyan/cli/main.py` + `src/songyan/services/doctor_service.py` 做 diff-only 审查，发现 1 个 P2（schema 只验表名），已通过 drift 检测修复并补回归测试；报告生成于 `.tmp/code_guard_180/report.html` / `.tmp/code_guard_180/report.md`。

### 验证结果（2026-07-20）

| 项 | 结果 |
|---|---|
| Task 180 聚焦 doctor 测试 | `python -m pytest tests/cli/test_doctor_command.py -q` → **12 passed** |
| Ruff | `ruff check src/ tests/` → **All checks passed** |
| 默认全量 pytest | `powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 1800 -DetectPytestSummary -- python -m pytest tests/ -q` → **2903 passed, 2 skipped, 1 xfailed, 7 warnings**；`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| Code review | `bits-code-guard` diff-only review → 1 P2 found and fixed |

## 验收判据

- `songyan doctor` 默认不发真实 LLM 请求。
- 缺 API key、非法 DB URL、资源缺失时能在首次 LLM 调用前给出可读错误。
- 已存在 DB 可做 schema 检查；默认不主动迁移源库；只有 `--init-db` 才初始化/迁移。
- `--json` 可被脚本解析，summary 与 exit code 一致。
- 聚焦 doctor 测试通过，默认全量测试与 Ruff 通过。
- `tasks/V9-README.md`、`docs/STATUS.md`、`README.md`、`docs/INDEX.md` 同步 Task 180 状态与证据。

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| doctor 默认写入用户 DB | 测试发现未传 `--init-db` 也调用 `init_schema()` | 立即改为只读/临时探针；写库必须 opt-in |
| LLM 连通性测试消耗 API | 默认 doctor 调用了真实 LLM | 改为 `--check-llm` 显式 opt-in，并在测试中 mock probe |
| Windows 路径权限测试不稳定 | 不同机器表现不同 | 将低层路径可写逻辑封装成 helper，单测 monkeypatch helper 返回结果 |
| 输出过于冗长 | README/CLI 输出变诊断手册 | console 保持 summary + hint，细节放 JSON |
| 与 Task 181 CLI 测试清零范围混淆 | 需要修改 `pyproject` 默认忽略或旧 CLI 用例 | 停止扩大范围；只新增 doctor 聚焦测试，Task 181 统一清理 CLI 测试策略 |

## Out of Scope

- CI workflow 与 badge。
- `tests/cli/test_cli.py` 全文件既有失败清零。
- 真实 LLM 生成 smoke。
- Profile 调参 CLI。
- 五门工具收编。

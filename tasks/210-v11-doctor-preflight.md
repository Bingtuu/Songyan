# Task 210 - V11 doctor / preflight 增强

> **阶段**: V11 开源可用化收尾
> **状态**: DONE
> **依赖**: Task 208 readiness audit；Task 209 Quickstart 与用户文档闭环
> **目标**: 让外部技术用户在运行生成前能通过 `doctor` / preflight 得到结构化、可操作的本地环境诊断，并修正 run 业务失败仍返回 0 的误导性 exit code。

---

## 任务目标

完成 V11 Task 210 doctor / preflight 增强：

1. 修复非法配置导致的 CLI 导入期 traceback，尤其是非法 `CHECKPOINTER_MODE`。
2. 强化 `songyan doctor` 对配置、DB/schema、资源、日志路径、预算和 LLM 前置条件的结构化诊断。
3. 让 `songyan run` 在进入生成 pipeline 前做 preflight。
4. 让 `songyan run` 在业务失败、partial 或 failed run 时返回非 0 exit code。
5. 产出任务书、命令证据、测试证据和 DONE 文档。

---

## 范围

包含：

- 配置加载错误从导入期异常变成 `doctor` / preflight 诊断。
- `doctor --json` 保持机器可读输出，human 输出保持可读。
- `doctor` 增加日志路径与成本预算检查。
- run preflight 覆盖 LLM key、DB/schema、资源、日志路径、预算、runtime checkpointer 和项目存在性。
- run 最终状态为 `partial` / `failed` 或存在失败章节时返回 exit code 1，并保留 `run_id` 输出。
- CLI / service 测试与本地命令证据。

不包含：

- 不扩张核心生成能力。
- 不新增核心 Agent / Workflow 节点。
- 不修改 prompt、CED、T9、five-gate、segment audit 或质量 hard gate。
- 不实现 backup/restore；该能力路由到 Task 211。
- 不实现失败恢复完整分类；该能力路由到 Task 212。
- 不实现 run bundle / 脱敏诊断包；该能力路由到 Task 213。
- 不实现 profile validate / rollback / history；该能力路由到 Task 214。
- 不实现 wheel smoke、release checklist、CHANGELOG、CONTRIBUTING 或 issue templates；这些路由到 Task 215。

---

## 当前缺口

来自 Task 208/209 与本地复核：

| 缺口 | 当前表现 | 本任务处理 |
|------|----------|------------|
| 非法 `CHECKPOINTER_MODE` | CLI 导入期 Pydantic traceback | 转为 `doctor` / preflight fail |
| 缺 key run | pipeline 记录失败，但进程 exit code 仍可能为 0 | preflight 阻断；pipeline 后失败也 exit 1 |
| 日志路径 | `doctor` 未明确检查 `logs/` 可写性 | 增加 `logs.path` |
| 成本预算 | `doctor` 未明确检查 `SONGYAN_RUN_COST_BUDGET` / `RUN_COST_BUDGET` 合法性 | 增加 `runtime.budget` |
| run 前置条件 | run 主要依赖 pipeline 内部失败 | 增加 CLI preflight |

---

## 验收标准

必须满足：

- `CHECKPOINTER_MODE=invalid songyan doctor --json` exit 1，输出 JSON，包含配置/运行时失败项，无 traceback。
- 缺 `LLM_API_KEY` 时 `songyan doctor --json` exit 1，包含 `llm.key` fail 和 hint。
- 非法预算值时 `songyan doctor --json` exit 1，包含 `runtime.budget` fail。
- `songyan run` 在缺 key、DB/schema 不可用、项目不存在等 preflight 失败时 exit 1，不进入 pipeline。
- `songyan run` 在 pipeline 返回 `partial` / `failed` 时保留 `run_id` 输出并 exit 1。
- 成功 run 保持 exit 0。
- 现有 Quickstart 文档口径仍成立，Task 211-215 缺口不被误标为完成。

验证命令：

```powershell
python -m pytest tests/cli -q
python -m pytest tests/test_119_reporting_wrapper.py tests/test_175_cost_tracking.py tests/test_phase2_graph.py -q
ruff check src/ tests/
```

若配置加载影响面超预期，再执行：

```powershell
python -m pytest tests/ -q
```

---

## 交付物

- `tasks/210-v11-doctor-preflight.md`
- `tasks/210-v11-doctor-preflight-DONE.md`
- `docs/reports/210-doctor-preflight-evidence.md`
- 相关代码和测试
- `docs/STATUS.md`、`docs/INDEX.md`、`tasks/V11-README.md`、`docs/quickstart.md`、`docs/troubleshooting.md` 的状态同步

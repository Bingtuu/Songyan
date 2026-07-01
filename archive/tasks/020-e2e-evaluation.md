# Task 020: 端到端集成测试 + 评测集

> **Phase**: Phase 4 — 评测与优化
> **优先级**: P0
> **依赖**: Task 001 ~ 019（全部完成）
> **预计工作量**: 大

---

## Goal

用 mock 数据跑通完整的单章闭环流程，验证 LangGraph 工作流各节点衔接正确；然后准备 3 个种子项目评测集，收集客观验收指标。

## Context

Task 019 已完成 LangGraph 编排（12 节点状态机）和 SummaryWriter。所有 Agent 独立测试均已通过（617 tests）。但当前尚未验证：

1. **端到端流程**：从 `run_chapter_pipeline()` 到 `done`，各节点通过 ID 从 DB 加载数据的链路是否正确
2. **循环路径**：revision → rule_auditor → llm_auditor → review_merger 循环是否能在 2 轮后正确退出
3. **人工确认恢复**：interrupt → `Command(resume)` → 继续执行的 checkpoint 恢复机制
4. **验收指标**：无法测量"设定硬错误数 = 0""审查漏检率 < 35%"等关键指标

本 Task 是 V1.0 MVP 的最后一个工程 Task，完成后进入真实题材评测阶段。

---

## In Scope（必须完成）

### 1. Mock 端到端集成测试

- [ ] **完整路径 A（无 issue）**：goal_planner → creative_director → context_manager → writer → rule_auditor → llm_auditor → review_merger → literary_auditor → revision_router(pass) → human_confirm(accept) → settlement_extractor → done
  - Mock 所有 LLM 调用（`call_llm`）和 DB 写入（通过 patch repository）
  - 验证最终 state 包含正确的 `settlement_id` 和 `summary_id`
  - 验证 chapter_head 指向 accepted_version

- [ ] **完整路径 B（1 轮修订）**：同上，但 review_merger 产出 critical issue → revision_handler 执行 patch → 第二轮 rule_auditor → llm_auditor → review_merger(pass) → human_confirm
  - 验证 revision_round = 1
  - 验证 current_version_id 已更新为新版本

- [ ] **完整路径 C（2 轮修订后退出）**：revision_merger 连续 2 轮产出 critical → 第 3 轮 router 强制 pass → human_confirm
  - 验证 revision_round = 2（不超过 2）

- [ ] **完整路径 D（reject）**：human_confirm(reject) → 回到 goal_planner → 重新执行
  - 验证 state 被正确重置（revision_round = 0）

- [ ] **完整路径 E（back）**：human_confirm(back) → 回到 writer → 生成新版本
  - 验证 writer 重新组装 ContextPackage 并生成新版本

- [ ] **完整路径 F（edit）**：human_confirm(edit) → 调用编辑器 → settlement_extractor
  - 验证 edited version 被保存，version_type = "edited"

### 2. Checkpoint 恢复测试

- [ ] **中断恢复**：workflow 执行到 human_confirm 前中断，进程重启后从 checkpoint 恢复，传入 `Command(resume="accept")` 继续执行
- [ ] **状态一致性**：恢复后的 state 与中断前完全一致

### 3. 评测集基础设施

- [ ] **评测 runner**：`evals/runner.py`，支持运行单个种子项目并收集指标
- [ ] **种子项目配置**：3 个预置项目配置（JSON），可直接导入数据库
  - 种子 1：xuanhuan + webnovel（完整配置，主验收）
  - 种子 2：urban + hybrid（基础配置，验证跨题材）
  - 种子 3：scifi + webnovel（基础配置，验证跨题材）
- [ ] **人工种子章节**：每个种子项目预置 1 章人工撰写的种子正文（作为 Chapter 1），用于触发 Chapter 2 的生成

### 4. 验收指标收集

评测 runner 必须能收集以下指标：

| 指标 | 目标 | 测量方式 |
|------|------|----------|
| 流程跑通率 | 100% | 3 个种子项目均能完成完整闭环 |
| 设定硬错误数 | 0 | critical world_consistency = 0 |
| AI 腔规则命中数 | < 2 处/章 | RuleAuditor 检测数 |
| 疲劳词命中数 | < 3 处/章 | RuleAuditor 检测数 |
| 首屏钩子达标率 | 100% | 前 300 字有吸引力事件 |
| 章末钩子达标率 | 100% | 最后 200 字有有效悬念 |
| 状态结算字段准确率 | > 90% | old_value 与 DB 一致率 |
| 状态结算 setting_key 准确率 | > 90% | setting_key 唯一 + source_quote 存在 |
| 概念空转段落数 | 0 | LiteraryAuditor 检测数 |
| 修订后新问题数 | 0 | 第二轮审查新问题数 = 0 |

### 5. 集成性能测试

- [ ] 单章完整闭环（mock LLM）总耗时 < 5 秒
- [ ] RuleAuditor + LLMAuditor + ReviewMerger + LiteraryAuditor 串联耗时 < 40 秒（mock LLM 时 < 1 秒）

---

## Out of Scope（明确不做）

- 真实 LLM 调用跑评测（本 Task 只用 mock，真实 LLM 评测在 V1.0 验收阶段手动执行）
- Web UI / TUI
- PostgreSQL / Redis / Qdrant
- 多模型路由
- V1.5+ 功能（PolyphonyPlanner、ForeshadowingManager 等）
- 连续多章生成（V1.0 只验证单章闭环）

---

## 接口契约

```python
# evals/runner.py
async def run_seed_project(
    project_config_path: str,
    seed_chapter_path: str,
    output_dir: str,
) -> EvaluationResult:
    """运行单个种子项目的评测.

    1. 导入项目配置到 SQLite
    2. 将种子章节作为 chapter 1 写入 DB
    3. 调用 run_chapter_pipeline 生成 chapter 2
    4. 收集所有验收指标
    5. 输出 EvaluationResult
    """
    ...

class EvaluationResult(BaseModel):
    project_id: str
    success: bool
    metrics: dict[str, float | int]
    chapter_version_id: str
    review_report_id: str
    settlement_id: str
    summary_id: str
    duration_ms: int
    logs: list[str]
```

---

## 测试要求

### Layer 1: 集成路径测试
- [ ] 路径 A（无 issue）mock 通过
- [ ] 路径 B（1 轮修订）mock 通过
- [ ] 路径 C（2 轮后退出）mock 通过
- [ ] 路径 D（reject）mock 通过
- [ ] 路径 E（back）mock 通过
- [ ] 路径 F（edit）mock 通过

### Layer 2: Checkpoint 测试
- [ ] 中断后 resume 成功
- [ ] 状态一致性验证

### Layer 3: 评测集测试
- [ ] 种子项目配置可正确导入
- [ ] 评测 runner 能收集所有指标
- [ ] 性能测试通过

---

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_integration.py -v` 全部通过（6 条路径 + checkpoint + 性能）
- [ ] `pytest tests/test_eval_runner.py -v` 全部通过
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 更新了 docs/STATUS.md
- [ ] 更新了 README.md（Phase 4 完成状态）
- [ ] 生成了 tasks/020-e2e-evaluation-DONE.md 交接文件

---

## 参考文档

- `docs/architecture/04-vibe-coding-engineering.md` — 工程手册 + 验收指标
- `system_prompt/development-tech-plan-v2.md` — V2 技术方案第 9~10 章
- `src/songyan/workflows/phase1_graph.py` — LangGraph 编排入口
- `src/songyan/workflows/_nodes.py` — 12 个节点函数

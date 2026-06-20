# Task 118: ContinuityAuditor Health 低分治理策略

> **Phase**: V5.0 Phase 4 — 质量信号治理
> **优先级**: P2
> **依赖**: Task 117 完成
> **预计工作量**: 1-2 天

---

## Goal

梳理 Task 114c 中持续出现的 `continuity.health_low` 信号，明确其在 V5.0 收口阶段应作为软复核、人工 marks 还是 QualityGate 子门禁，并建立可追踪、可测试、可解释的治理流程。

## Context

Task 114c DONE 记录：多个章节出现 ContinuityAuditor health 低分，目前只写 human marks，不阻断 accept。这一策略保证了长跑完成率，但也可能掩盖跨章一致性质量下降。

V5.0 的核心目标不是单纯跑完 150 章，而是在 Context Diet 2.0 的信息节食机制下保持长篇叙事的连续性。health_low 必须有明确处理策略，否则 V5.0 最终验收会缺少质量风险解释。

## In Scope（必须完成）

- [ ] 统计 Task 114c Ch111-Ch150 中 health_low 出现章节、频率和类型。
- [ ] 抽样读取对应章节的 continuity marks，判断真实质量影响。
- [ ] 定义 health_low 的分级策略：记录、软复核、阻断。
- [ ] 明确 human marks 的字段、来源、可追踪路径和清理规则。
- [ ] 补充报告指标，使 health_low 能在 DG 报告中稳定展示。
- [ ] 补充测试，验证 health_low 不会被静默吞掉。

## Out of Scope（明确不做）

- 不把所有 health_low 直接升级为硬门禁。
- 不重写 ContinuityAuditor 评分模型。
- 不修改 LLMAuditor 或 RuleAuditor 的核心评分权重。
- 不处理 ContextEmergency 或 best-version 问题。

## 实现方案

### 1. 现状统计

从以下来源收集 health_low：

- `logs/chapter_runs/*.jsonl`
- DB human marks 表
- continuity auditor 输出
- Task 114c stdout/stderr

输出统计：

| 指标 | 说明 |
|------|------|
| health_low_count | Ch111-Ch150 出现次数 |
| affected_chapters | 受影响章节 |
| mark_type | 标记类型 |
| severity | 严重程度 |
| accepted_after_mark | 是否仍 accepted |

### 2. 分级策略

建议采用三档：

| 等级 | 条件 | 处理 |
|------|------|------|
| P3 记录 | 低置信或轻微连续性疑点 | 写 human mark，不阻断 |
| P2 软复核 | 同章多次 health_low 或涉及主线事实 | accepted 后进入复核清单 |
| P1 阻断候选 | 涉及角色生死、设定硬冲突、重大时间线冲突 | 不直接阻断，先进入人工确认或专项 QG |

V5.0 收口阶段默认不新增硬阻断，除非 Task 118 发现 health_low 与实际重大矛盾高度相关。

### 3. 报告接入

在 streaming report 中增加或校正：

- health_low 次数
- affected chapters
- human marks count
- unresolved marks count
- P1/P2/P3 分级统计

### 4. 数据一致性

确保 human marks：

- 关联 `project_id`
- 关联 `chapter_number`
- 关联 `version_id`
- 包含 auditor 来源
- 包含 severity
- 可在报告中复现

## 接口契约

```python
def classify_continuity_mark(mark: dict[str, object]) -> str:
    """将 continuity mark 分类为 P1/P2/P3."""
    ...
```

```python
def collect_continuity_health_metrics(
    project_id: str,
    chapter_start: int,
    chapter_end: int,
) -> dict[str, object]:
    """收集指定章节范围内的 continuity health 指标."""
    ...
```

若现有 report/repository 已有等价接口，应优先复用。

## 数据模型

原则上复用现有 human mark 模型。若缺少 severity 或来源字段，可补充轻量字段：

```python
class ContinuityHealthMark(BaseModel):
    project_id: str
    chapter_number: int
    version_id: str
    severity: Literal["P1", "P2", "P3"]
    source: str = "continuity_auditor"
    message: str
    resolved: bool = False
```

## 执行流程

1. **统计基线**
   - 扫描 Ch111-Ch150 health_low。
   - 生成统计表和受影响章节清单。

2. **样本复核**
   - 抽样读取 P1/P2 候选章节。
   - 判断 marks 是否对应真实文本风险。

3. **策略制定**
   - 确定 health_low 在 V5.0 的最终处理口径。
   - 明确哪些情况进入 V5.1。

4. **实现补强**
   - 补齐分类、报告和数据追踪。
   - 不引入不必要的新门禁。

5. **验证与文档**
   - 运行聚焦测试。
   - 生成 `tasks/118-continuity-health-governance-DONE.md`。
   - 更新 V5 状态入口。

## 测试要求

### Layer 1: 分类测试

- [ ] 轻微措辞问题分类为 P3。
- [ ] 主线事实疑点分类为 P2。
- [ ] 重大硬冲突分类为 P1 候选。

### Layer 2: 数据追踪测试

- [ ] health_low 写入 human mark 后可通过 project/chapter/version 查询。
- [ ] resolved 状态可更新。
- [ ] 缺失 version_id 的 mark 不进入最终报告，或被标记为 invalid。

### Layer 3: 报告测试

- [ ] streaming report 能稳定展示 health_low 统计。
- [ ] 报告统计与 DB human marks 一致。

## 验收标准（Acceptance Criteria）

| 指标 | 目标 |
|------|------|
| Ch111-Ch150 health_low 统计 | 100% 可复现 |
| human marks 可追踪性 | 100% 关联 project/chapter/version |
| 分级策略 | P1/P2/P3 规则明确并有测试覆盖 |
| 误阻断 | V5.0 不因未验证 health_low 直接阻断 accepted |
| 报告 | DG 报告展示 health_low 和 unresolved marks |
| 测试 | 聚焦测试通过；`ruff check src/ tests/` 通过 |

## 风险与应对

| 风险 | 应对 |
|------|------|
| 过早升级为硬门禁导致成功率下降 | V5.0 先采用软复核，V5.1 再决定硬门禁 |
| human marks 堆积不可维护 | 增加 severity、resolved 和报告统计 |
| 低分与真实质量问题相关性不明 | 抽样人工阅读，不只看机器分 |

## 参考文档

- `tasks/114-ch101-ch150-streaming-validation-DONE.md`
- `tasks/117-dg2-risk-window-revalidation.md`
- `src/songyan/agents/continuity_auditor/`
- `src/songyan/evals/streaming_report.py`

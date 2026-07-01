# Task 051 — A/B 测试脚本 + 评估报告

> **目标**: 用受控实验验证 RAG 自动层对长篇小说一致性的实际提升效果，输出可量化的 A/B 对比报告。  
> **Phase**: 8b  
> **优先级**: P1  
> **依赖**: Task 050（RAGRetriever + ContextManager 集成）  
> **预计工作量**: 中（2~3 天）

---

## Context

Phase 8b 的核心假设是：RAG 自动层能显著降低 30+ 章后的设定遗忘率和一致性断裂。本 Task 负责用**受控实验**验证这一假设。

**实验设计**（来自 `docs/architecture/phase8b_rag_layer.md`）：
- **对照组（A）**: 关闭 RAG，仅用现有分层摘要 + 人类标记
- **实验组（B）**: 开启 RAG，完整 D+B 混合架构
- **控制变量**: 同一 seed、同一 genre、同一 creative mode、连续章节（如 Ch12~Ch20）

**评估指标**:
1. **设定遗忘率** = orphaned_settings / setting_tracking 总数
2. **连续性健康分** = ContinuityAuditor `overall_health_score`
3. **设定保留率** = 早期设定在后续章节中的正确引用率（由 `evals/consistency_test.py` 随机抽样验证）

**成功标准**:
- 设定遗忘率降低 ≥ 20%
- 连续性健康分提升 ≥ 0.5 分
- 设定保留率提升 ≥ 10%

> **范围说明**: Ch12~Ch30（19 章 × 2 组 = 38 章生成），确保实验组至少有 10 章在 RAG 阈值以上，ContinuityAuditor 产生 ~6 次审计数据点。如时间和成本受限，可先做 Ch12~Ch20 快速验证，再扩展到 Ch30。

---

## Goal

构建可一键运行的 A/B 测试脚本，在同一项目 seed 上分别运行"关闭 RAG"和"开启 RAG"两批章节，自动收集连续性指标并生成对比报告。

---

## In Scope（必须完成）

### 1. A/B 测试脚本（`evals/rag_ab_test.py`）
- [ ] `RAGABTest` 类
- [ ] `run_control(project_id, seed_config, chapter_range) -> ControlResult` — 对照组（RAG 关闭）
- [ ] `run_experiment(project_id, seed_config, chapter_range) -> ExperimentResult` — 实验组（RAG 开启）
- [ ] `compare(control, experiment) -> ComparisonReport` — 对比分析
- [ ] 测试前自动清理：删除已有章节向量索引、重置 continuity_reports，确保两组起点一致
- [ ] 支持 `--chapters 12-30` 指定章节范围（**19 章**，确保实验组至少 10 章在 RAG 阈值以上）
- [ ] 支持 `--sample-count 20` 随机抽样验证设定保留率
- [ ] 支持 `--genre xuanhuan` 补充跨题材快速验证（缩小范围到 Ch12~Ch20，3 章 × 2 组）

### 2. 新增评估指标（`evals/metrics.py`）
- [ ] `setting_forget_rate` — 设定遗忘率
- [ ] `continuity_health_score` — 连续性健康分（读取 ContinuityAuditor 报告）
- [ ] `setting_retention_rate` — 设定保留率（随机抽样验证）
  - 抽样方案：从 `setting_tracking` 表中选取 Ch1~Ch10（早期）埋设的设定，随机抽取 20 个
  - 判断标准：在后续章节（Ch12~Ch30）中，该设定是否被正确引用（精确匹配设定名或语义等价）
  - 自动化判断：先用关键词匹配快速筛选，有歧义时人工标注（至少 1 人）
- [ ] `rag_retrieval_precision`（可选）— RAG 返回 chunk 中真正相关的比例（人工标注 Top-5）

### 3. ContinuityAuditor 增强（如需要）
- [ ] 确保 ContinuityAuditor 的 `overall_health_score` 计算稳定（Ch12~Ch20 范围）
- [ ] 如 health_score 算法有边界问题，在本 Task 中修复

### 4. 报告生成（`evals/rag_ab_test.py`）
- [ ] `ComparisonReport.to_markdown() -> str` — 生成标准 Markdown 报告
- [ ] 报告内容：
  - 实验配置（seed、genre、章节范围、RAG 配置）
  - 对照组 vs 实验组的指标对比表
  - 逐章连续性健康分曲线图（文本表格或 ASCII 图）
  - 显著性判断（是否达到成功标准）
  - 失败案例分析（如：哪些设定 RAG 未能拯救）
  - 下一步建议（是否进入 Phase 9，或调优 RAG 参数）

### 5. 报告输出
- [ ] `docs/review/rag_ab_test_report.md` — 本次 A/B 测试的正式报告
- [ ] `evals/output/rag_ab_test_{timestamp}.json` — 结构化原始数据（便于后续复现）

### 6. 复现脚本
- [ ] `scripts/run_rag_ab_test.sh` — 一键运行 A/B 测试的 shell 脚本
- [ ] 包含环境检查（模型是否下载、DB 是否就绪）

---

## Out of Scope（明确不做）

- 不修改 Chunker / Embedder / VectorStore（属于 Task 049）
- 不修改 RAGRetriever / ContextManager（属于 Task 050）
- 不修改 Writer 核心逻辑（除非评估发现严重问题，需新开 Task）
- 不做人类盲测评分（成本过高，本 Task 以自动指标为主）
- 不做多 genre / 多 seed 的大规模测试（1 个 seed + 1 个 genre 作为 Phase 8b 验收）
- 不做统计显著性检验（样本量不足，以绝对指标差值为主）

---

## 接口契约

```python
# evals/rag_ab_test.py

class RAGABTest:
    def __init__(
        self,
        seed_config: SeedProjectConfig,
        chapter_range: tuple[int, int],
        rag_config_experiment: RAGConfig,
    ) -> None: ...

    async def run_control(self) -> ControlResult: ...

    async def run_experiment(self) -> ExperimentResult: ...

    async def run(self) -> ComparisonReport:
        """运行完整 A/B 测试并返回对比报告."""
        ...


@dataclass
class ControlResult:
    project_id: str
    chapters: list[int]
    setting_forget_rate: float
    continuity_health_scores: dict[int, float]  # chapter -> score
    setting_retention_rate: float
    raw_continuity_report: ContinuityReport


@dataclass
class ExperimentResult:
    project_id: str
    chapters: list[int]
    setting_forget_rate: float
    continuity_health_scores: dict[int, float]
    setting_retention_rate: float
    raw_continuity_report: ContinuityReport
    avg_rag_results_per_chapter: float  # 平均每章检索到的 chunk 数


@dataclass
class ComparisonReport:
    control: ControlResult
    experiment: ExperimentResult
    setting_forget_rate_delta: float      # 负数 = 降低
    continuity_health_delta: float        # 正数 = 提升
    setting_retention_delta: float
    meets_success_criteria: bool
    failure_cases: list[FailureCase]
    recommendations: list[str]

    def to_markdown(self) -> str: ...


@dataclass
class FailureCase:
    chapter: int
    setting_key: str
    control_status: str   # "forgotten" | "mismatched"
    experiment_status: str
    rag_chunks: list[str]  # RAG 检索到的相关段落（如有）
    diagnosis: str         # 为什么 RAG 未能拯救
```

---

## 数据模型

```python
# evals/models.py — 扩展现有模型

class RAGABTestConfig(BaseModel):
    """A/B 测试配置（可序列化复现）."""

    seed_project_path: str
    genre_id: str
    creative_mode_id: str
    chapter_range: tuple[int, int]
    sample_count: int = 20   # 随机抽样验证的设定数
    rag_config: RAGConfig

class RAGABTestResult(BaseModel):
    """结构化测试结果（JSON 输出）."""

    timestamp: str
    config: RAGABTestConfig
    control: ControlResult
    experiment: ExperimentResult
    comparison: ComparisonReport
```

---

## 实现清单

### 1. 评估指标扩展
- [ ] `evals/metrics.py`: 新增 `setting_forget_rate`, `continuity_health_score`, `setting_retention_rate`
- [ ] `evals/consistency_test.py`: 复用随机抽样逻辑，计算设定保留率

### 2. A/B 测试框架
- [ ] `evals/rag_ab_test.py`: `RAGABTest` 主类
- [ ] `evals/rag_ab_test.py`: `ComparisonReport` 报告生成

### 3. 辅助脚本
- [ ] `scripts/run_rag_ab_test.sh`: 一键运行脚本
- [ ] 环境检查：模型下载、DB 连接、seed 项目存在性

### 4. 报告输出
- [ ] `docs/review/rag_ab_test_report.md`: 报告模板
- [ ] `evals/output/`: 结构化 JSON 输出

---

## 测试要求

### Layer 1: 模型测试
- [ ] `test_rag_ab_test_config_serialization`: 配置可 JSON 序列化/反序列化
- [ ] `test_comparison_report_markdown`: 报告 Markdown 包含所有必填字段

### Layer 2: 模块测试
- [ ] `test_metrics_setting_forget_rate`: 给定模拟 continuity report，正确计算遗忘率
- [ ] `test_metrics_setting_retention_rate`: 随机抽样逻辑正确
- [ ] `test_comparison_meets_criteria`: 达到成功标准时 `meets_success_criteria=True`
- [ ] `test_comparison_fails_criteria`: 未达到时正确标记

### Layer 3: 集成测试（Mock）
- [ ] `test_ab_test_run_mock`: Mock pipeline 运行，验证完整 A/B 流程无异常
- [ ] `test_ab_test_cleanup`: 验证测试前清理逻辑正确（删除旧向量、重置报告）

---

## 验收标准

- [ ] `pytest tests/evals/test_rag_ab_test.py -v` 全部通过（Mock 测试）
- [ ] `python evals/rag_ab_test.py --seed evals/seeds/orbital_horror.yaml --chapters 12-30` 在真实环境可运行（可能耗时较长，不要求 CI 跑）
- [ ] `docs/review/rag_ab_test_report.md` 已生成，包含明确结论
- [ ] 达到成功标准 **或** 提供了不达标的原因分析 + 调优建议
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 更新了 `docs/STATUS.md`（Task 051 状态改为 ✅，Phase 8b 整体状态更新）
- [ ] 更新了 `docs/architecture/phase8b_rag_layer.md`（如 A/B 结果导致设计调整）
- [ ] 生成了 `tasks/051-rag-ab-test-evaluation-DONE.md` 交接文件

---

## 已知限制与风险

| 风险 | 说明 | 应对 |
|------|------|------|
| A/B 测试耗时长 | Ch12~Ch20 共 9 章 × 2 组 = 18 章完整生成，可能数小时 | 脚本支持断点续跑；支持 `--dry-run` 仅用 Mock 验证流程 |
| API 成本高 | 18 章 LLM 调用，成本不可忽略 | 测试前确认预算；支持缩小范围到 Ch12~Ch15（6 章 × 2 组） |
| 结果不显著 | 9 章可能不足以暴露 RAG 优势 | 报告中明确样本量限制；如不达标给出调优方向 |
| ContinuityAuditor 评分不稳定 | health_score 算法可能在不同运行间波动 | 测试前确认算法确定性；必要时固定随机种子 |

---

## 参考文档

- `docs/architecture/phase8b_rag_layer.md` — Phase 8b 设计文档（含 A/B 测试方案）
- `docs/architecture/long_range_research_report.md` — Task 039 调研报告
- `tasks/050-rag-retriever-integration.md` — Task 050 RAG 集成
- `evals/runner.py` — 现有评估 runner（参考 pipeline 运行逻辑）
- `evals/consistency_test.py` — 随机一致性测试引擎（复用抽样逻辑）
- `evals/metrics.py` — 现有 metrics 框架

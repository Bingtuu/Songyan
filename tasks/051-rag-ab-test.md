# Task 051: RAG A/B Test Evaluation

## Objective
实现 RAG 自动检索层（Task 050）的 A/B 测试框架，验证其对长篇小说一致性的提升效果。

## Success Criteria
| 指标 | 对照组 (RAG 关闭) | 实验组 (RAG 开启) | 目标变化 |
|------|------------------|------------------|---------|
| 设定遗忘率 | 基准值 | 实验值 | 降低 ≥ 20% |
| 连续性健康分 | 基准值 | 实验值 | 提升 ≥ 0.5 |
| 设定保留率 | 基准值 | 实验值 | 提升 ≥ 10% |

## Implementation

### 新增文件
- `evals/rag_ab_test.py` — A/B 测试核心框架
  - `RAGABTest` 类：运行对照组与实验组
  - `ComparisonReport` 类：生成 Markdown + JSON 报告
  - `FailureCase` / `ControlResult` / `ExperimentResult` 数据类
  - CLI 入口支持 `--seed-config`, `--seed-chapter`, `--chapters`, `--dry-run`

- `scripts/run_rag_ab_test.sh` — 一键运行脚本

- `tests/evals/test_rag_ab_test.py` — 10 个单元测试
  - 报告 Markdown 渲染
  - Dry-run 快速验证
  - 环境变量隔离
  - 成功标准判断

### 关键设计决策
1. **项目隔离**：对照组和实验组各自创建独立 project_id，避免数据污染
2. **RAG 开关控制**：通过 `SONGYAN_RAG_MODE` 环境变量在 `never` / 默认之间切换
3. **指标收集**：
   - 设定遗忘率 = `orphaned_settings / active_settings`
   - 连续性健康分 = `ContinuityAuditor.audit()` 的 `overall_health_score`
   - 设定保留率 = `1 - forget_rate`
4. **Dry-run 模式**：Mock 运行，不调用 LLM，用于快速验证框架逻辑
5. **失败案例分析**：自动提取实验组仍 orphaned 的设定，给出诊断建议

### 报告输出
- Markdown 报告：`evals/output/rag_ab_test_{timestamp}.md`
- JSON 数据：`evals/output/rag_ab_test_{timestamp}.json`

## Test Results
```
pytest tests/evals/test_rag_ab_test.py -v
============================= 10 passed in 18.32s =============================
```

相关套件回归：
```
pytest tests/evals/ tests/rag/ tests/db/test_chunk_repo.py tests/test_settlement_indexing.py tests/test_context_manager_rag.py tests/test_writer_prompt_rag.py -q
============================= 109 passed in 85.81s =============================
```

## Usage

### Dry-run 快速验证
```bash
bash scripts/run_rag_ab_test.sh evals/seeds/xuanhuan_webnovel.json evals/seeds/chapters/xuanhuan_ch1.md 12-20 webnovel evals/output dry_run
```

### 实际 A/B 测试（需要 LLM API）
```bash
bash scripts/run_rag_ab_test.sh evals/seeds/xuanhuan_webnovel.json evals/seeds/chapters/xuanhuan_ch1.md 12-30 webnovel evals/output
```

或直接调用 Python：
```bash
python -m evals.rag_ab_test \
  --seed-config evals/seeds/xuanhuan_webnovel.json \
  --seed-chapter evals/seeds/chapters/xuanhuan_ch1.md \
  --chapters 12-30 \
  --mode-id webnovel \
  --output-dir evals/output
```

## Next Steps
1. 使用真实 LLM 运行 A/B 测试（预计耗时较长，每章生成约 1-2 分钟）
2. 根据结果调优 RAG 参数（min_similarity, max_results, chunk_overlap）
3. 若达到成功标准，进入 Phase 9 全面部署

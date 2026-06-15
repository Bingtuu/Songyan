# Task 051 — A/B 测试脚本 + 评估报告

> **状态**: ✅ 已完成（代码实现 + 测试通过）
> **完成时间**: 2026-06-03（随 Milestone 15 合并）
> **实际工作量**: 中（2~3 天）

---

## 交付物

| 文件 | 说明 |
|------|------|
| `evals/rag_ab_test.py` | A/B 测试核心框架，`RAGABTest` 主类 |
| `tests/evals/test_rag_ab_test.py` | 10 个单元测试，全部通过 |
| `scripts/run_rag_ab_test.sh` | 一键运行脚本 |
| `evals/metrics.py` | 新增 `setting_forget_rate`, `continuity_health_score`, `setting_retention_rate` |

## 测试结果

```
pytest tests/evals/test_rag_ab_test.py -v
============================= 10 passed in 18.32s =============================
```

## 使用方式

### Dry-run 快速验证
```bash
bash scripts/run_rag_ab_test.sh evals/seeds/xuanhuan_webnovel.json evals/seeds/chapters/xuanhuan_ch1.md 12-20 webnovel evals/output dry_run
```

### 实际 A/B 测试（需要 LLM API）
```bash
bash scripts/run_rag_ab_test.sh evals/seeds/xuanhuan_webnovel.json evals/seeds/chapters/xuanhuan_ch1.md 12-30 webnovel evals/output
```

## 已知限制

- 真实 LLM A/B 测试尚未运行（需要 API 调用和较长时间）
- 当前仅通过 Mock 测试验证框架逻辑

## 下一步

1. 使用真实 LLM 运行 A/B 测试（预计耗时较长，每章生成约 1-2 分钟）
2. 根据结果调优 RAG 参数（min_similarity, max_results, chunk_overlap）
3. 若达到成功标准，进入 Phase 9 全面部署

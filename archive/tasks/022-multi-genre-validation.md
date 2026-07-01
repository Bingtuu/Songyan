# Task 022: 多题材种子真实 LLM 评测

> **Phase**: Phase 4（评测优化循环）
> **优先级**: P0（阻塞 V1.0 完全交付）
> **依赖**: Task 021（Prompt v1.0.2 已验证通过）
> **预计工作量**: 中

---

## Goal

在玄幻和都市两个种子项目上运行真实 LLM 端到端评测，验证系统在科幻以外的题材上是否同样能完成闭环并达到 `is_pass=true`。

## Context

README 目标要求"3 个种子项目均完成闭环"，目前仅科幻新怪谈跑通（Round 3, score 8.36）。玄幻和都市种子已在 `evals/seeds/` 中有配置文件，但尚未跑真实 LLM 评测。本 Task 是 V1.0 全面验收的最后一道关卡。

## In Scope（必须完成）

- [ ] 玄幻种子（xuanhuan）真实 LLM 端到端评测：运行完整 pipeline，收集 metrics
- [ ] 都市种子（urban）真实 LLM 端到端评测：运行完整 pipeline，收集 metrics
- [ ] 对比分析：三题材横向对比（score、issues、成本、耗时）
- [ ] 如果某题材 `is_pass=false`，定位根因并创建修复 Task
- [ ] 更新 `docs/STATUS.md` 评测历史表
- [ ] 更新 `README.md` 当前阶段描述

## Out of Scope（明确不做）

- 多章编排 — 留到 Task 023
- Prompt 细节打磨（scenes_count、dialogue_subtext 等）— 留到 Task 024
- 新题材 Profile 创建（已有 xuanhuan/urban/scifi）

## 接口契约

```python
# 复用现有 evals 基础设施
python -m evals --seed xuanhuan --prompt-version 1.0.2
python -m evals --seed urban --prompt-version 1.0.2
```

## 测试要求

### Layer 1: 无需新增模型

### Layer 2: 无需新增模块测试

### Layer 3: 集成验证
- [ ] 玄幻种子 pipeline 成功完成（`pipeline_success=1`）
- [ ] 都市种子 pipeline 成功完成（`pipeline_success=1`）
- [ ] 两题材均 `is_pass=true`

## 验收标准（Acceptance Criteria）

- [ ] 玄幻种子 `is_pass = true`
- [ ] 都市种子 `is_pass = true`
- [ ] 三题材横向对比报告写入 `evals/output/MULTI_GENRE_REPORT.md`
- [ ] 更新了 `docs/STATUS.md`
- [ ] 更新了 `README.md`
- [ ] 生成了 `tasks/022-multi-genre-validation-DONE.md` 交接文件

## 参考文档

- `docs/STATUS.md` — 当前评测历史与遗留问题
- `evals/` — 评测集基础设施
- `genres/xuanhuan.json` — 玄幻题材 Profile
- `genres/urban.json` — 都市题材 Profile

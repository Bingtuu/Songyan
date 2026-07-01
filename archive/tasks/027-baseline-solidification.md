# Task 027: 基线固化 — V2.0.0 Phase 0

> **Phase**: Phase 0 — 基线固化
> **优先级**: P0
> **依赖**: V1.x 全部完成（Task 026 结束）
> **预计工作量**: 中（1~2 小时）

---

## Goal

确保 V1.x 框架干净运行，建立可重复的评估基线，为 V2.0.0 各 Phase 的验证提供对照。

## Context

V1.x 完成了 Ch2~Ch11《轨道上的怪谈》的生成和评估，但过程中产生了大量临时文件、缓存、锁定的数据库。Phase 0 的目标是清理这些技术债务，确保框架在干净的起点上继续演进。

## In Scope（必须完成）

- [ ] 环境清理：解决 `songyan.db` 锁定问题（或创建新的开发数据库）
- [ ] 归档所有 `tasks/*-DONE.md` 到 `archive/tasks/`（如尚未归档）
- [ ] 清理残留的 `__pycache__`、`.pytest_cache`、egg-info
- [ ] 确认 `tests/` 全部通过（pytest -v）
- [ ] 创建 `scripts/evaluate_project.py` — 输入 project_id，输出基线指标：
  - 逐章字数/场景数/版本数统计
  - 跨章一致性扫描（orphaned settings, forgotten items）
  - 重复修辞检测（喃喃自语、呼吸停滞等）
  - 情绪曲线分析（基于情感词频）
  - 综合评分
- [ ] 运行基线评估，生成 `docs/review/baseline_orbital_horror.json`
- [ ] 确认所有新增 V2 功能可开关（backward compatible）

## Out of Scope（明确不做）

- 不修改任何 Agent 逻辑（Phase 1~6 再做）
- 不生成新章节（Phase 1 再做）
- 不修改 DB schema（Phase 3~4 再做）
- 不引入新依赖（Phase 4~6 评估后再决定）

## 接口契约

```python
# scripts/evaluate_project.py
async def evaluate_project(project_id: str) -> BaselineReport:
    """生成项目基线评估报告."""
    ...

class BaselineReport(BaseModel):
    project_id: str
    chapter_metrics: list[ChapterMetric]
    consistency_scan: ConsistencyScanResult
    style_analysis: StyleAnalysisResult
    overall_score: float
    generated_at: datetime
```

## 测试要求

- [ ] `pytest tests/ -v` 全部通过
- [ ] 评估脚本可在命令行独立运行：`python scripts/evaluate_project.py --project-id proj-3f17e980`
- [ ] 评估报告 JSON 可正确序列化/反序列化

## 验收标准（Acceptance Criteria）

- [ ] 测试通过率 100%
- [ ] `docs/review/baseline_orbital_horror.json` 已生成
- [ ] 代码符合 CLAUDE.md 规范
- [ ] 更新了 docs/STATUS.md
- [ ] 生成了 tasks/027-baseline-solidification-DONE.md 交接文件

## 参考文档

- `docs/architecture/roadmap_v2_phases.md` — V2 迭代路线图
- `docs/review/orbital_horror_ch2_ch11_assessment.md` — Ch2~Ch11 评估报告

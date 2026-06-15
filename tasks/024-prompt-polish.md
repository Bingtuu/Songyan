# Task 024: Prompt 细节打磨（scenes_count / dialogue_subtext / source_quote / rhythm）

> **Phase**: Phase 4（评测优化循环）
> **优先级**: P1（提升质量，不阻塞 V1.0）
> **依赖**: Task 022（多题材验证通过，有真实数据支撑）
> **预计工作量**: 中

---

## Goal

基于多题材验证的真实数据，针对 4 个已知缺陷进行 Prompt 或代码层调优，提升单章输出质量。

## Context

Round 3 科幻评测已暴露 4 个可优化项，虽然都不阻塞 `is_pass`，但影响读者体验。本 Task 在多题材验证完成后执行，确保优化有跨题材数据支撑，避免过度拟合科幻种子。

## In Scope（必须完成）

- [ ] **scenes_count ≥ 2**：Writer Prompt 强制要求仍被 LLM 忽略（只生成 1 场景）。尝试：
  - 在 Prompt 中增加「场景清单」预输出步骤
  - 或在代码层拆分（按时间/地点切换自动分场景）
- [ ] **dialogue_subtext 提升**：从 Round 3 的 6.0 提升到 7.0+
  - 在 Writer Prompt 中显式引用 CreativeDirector 输出的 `[角色语言指纹]`
  - 增加对话示例（含潜台词 vs 直白对比）
- [ ] **settlement source_quote 剩余 2 errors**：
  - 认知污染阶段、第71条安全协议的 source_quote 未在正文找到
  - 尝试：prompt 中增加「模糊匹配许可」规则，或代码层增加近似匹配回退
- [ ] **paragraph_rhythm 优化**：平均段落 41 字过短，单句段落 34% 过高
  - 调整 `QualityUtils` 中段落节奏检测阈值
  - 或在 Writer Prompt 中增加「段落长度分布」约束

## Out of Scope（明确不做）

- Craft Card 大版本升级（如 1.0.x → 1.1.0）— 本 Task 只做微调
- 新增 Auditor 维度
- 多章编排相关改动

## 接口契约

```python
# 复用现有 prompt loader 和 craft card 系统
# 只需更新 prompts/cards/*/1.0.x.yaml 和 manifests
# 以及 src/songyan/utils/quality.py 中的阈值
```

## 测试要求

### Layer 1: 无需新增模型

### Layer 2: 模块测试
- [ ] Prompt Loader 能正确加载更新后的版本
- [ ] QualityUtils 阈值调整后单元测试通过

### Layer 3: 集成测试
- [ ] 至少跑一轮真实 LLM 评测，验证 4 项指标有改善
- [ ] `is_pass` 不下降

## 验收标准（Acceptance Criteria）

- [ ] scenes_count 平均 ≥ 1.5（或代码层自动拆分生效）
- [ ] dialogue_subtext 评分 ≥ 7.0
- [ ] settlement validation_errors = 0
- [ ] paragraph_rhythm 平均段落长度 ≥ 50 字，单句段落占比 ≤ 25%
- [ ] `is_pass` 保持 true
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/024-prompt-polish-DONE.md` 交接文件

## 参考文档

- `prompts/cards/writer/1.0.2.yaml`
- `prompts/cards/llm_auditor/1.0.2.yaml`
- `prompts/cards/creative_director/1.0.2.yaml`
- `prompts/cards/settlement_extractor/1.0.1.yaml`
- `src/songyan/utils/quality.py`
- `evals/output/ROUND3_ANALYSIS_REPORT.md`

# Task 065: 未审 Agent 深审

> **Phase**: V3.x Layer 3 — 系统化质量守卫
> **优先级**: P2
> **依赖**: 无
> **预计工作量**: 中（2~3 天）

---

## Goal

对 V2.x 遗留未审查的 3 个 Agent 进行深度代码审查，确保规则合规性，输出审查报告并修复 P0 发现。

## Context

| Agent | 行数 | 审查重点 |
|-------|------|---------|
| `creative_director.py` | ~446 | 规则 17（不新增硬剧情事件）；`tension_gap` 标记；双重写入风险；prompt 变量注入完整性 |
| `rule_auditor.py` | ~335 | 规则 12（不做语义判断）；检测结果定位信息完整性；stimulus check 健壮性；genre.fatigue_words 注入链路 |
| `literary_auditor.py` | ~220 | 规则 14/27-30（不阻塞 accept、valuable_fissure、protected_elements 链路）|

## In Scope（必须完成）

- [ ] **`creative_director.py` 审查**:
  - 验证 `generate_creative_brief()` 不新增硬剧情事件（只基于 ChapterGoal 推导张力）
  - 验证 `tension_gap: true` 标记逻辑正确
  - 扫描是否有双重写入（同类 Pass 8 P0-1 模式）
  - 验证 prompt 变量注入完整性
- [ ] **`rule_auditor.py` 审查**:
  - 验证不做语义判断（纯代码检测）
  - 验证所有检测结果有定位信息（行号/段落/引用）
  - 验证 `PunchCheck` 健壮性（空 punch_points 不崩溃）
  - 验证 `genre.fatigue_words` 注入链路完整
- [ ] **`literary_auditor.py` 审查**:
  - 验证不阻塞 accept（返回值不触发 reject）
  - 验证 `valuable_fissure` 正确标记 `preserve=true`
  - 验证 `protected_elements` 正确注入 RevisionHandler
- [ ] **审查报告**: 按 Pass 7-9 模板输出
  - 发现摘要（优先级分布）
  - 逐项详述
  - 已确认合规项
- [ ] **P0 修复**: 审查中发现的 P0 级问题全部修复

## Out of Scope（明确不做）

- 不做 Prompt 内容审查（只审查代码逻辑）
- 不做性能优化
- P1/P2 发现可记录但不强制本 Task 修复

## 验收标准

- [ ] 3 个 Agent 审查报告归档至 `docs/review/v3_agent_audit_{agent}.md`
- [ ] P0 发现全部修复
- [ ] `pytest tests/ -x -q` 全部通过
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/061-agent-audit-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 7.2 未审 Agent 深审
- `AGENTS.md` — 规则 12, 14, 17, 27-30

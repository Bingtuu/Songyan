# Task 066: 跨切面合规扫描

> **Phase**: V3.x Layer 3 — 系统化质量守卫
> **优先级**: P2
> **依赖**: 无
> **预计工作量**: 小（0.5~1 天）

---

## Goal

对全项目进行跨切面规则合规扫描，输出扫描报告，标记违规项供后续 Task 决策优先级。

## Context

V3.x 需要一份"体检报告"，记录当前代码基线与 AGENTS.md 规则的差距。这份报告不作为强制修复清单，而是防止后续修改引入回退的参照物。

## In Scope（必须完成）

| 检查项 | 规则来源 | 方法 | 输出 |
|--------|---------|------|------|
| 文件长度超标 | 规则 64（<=400 行）| `find src/ -name "*.py" | xargs wc -l | sort -n` | 超限清单 |
| 裸 `except` | 规则 65 | `rg "except\s+Exception" src/ tests/ evals/` | 分类：合理 vs 不合理 |
| 类型标注完整性 | 规则 58 | 随机抽样 30 个函数签名 | 标注率 |
| `structlog` 使用 | 规则 67 | `rg "print\(" src/ tests/ evals/` | 残留清单 |

## Out of Scope（明确不做）

- 不强制全部修复（只标记，后续 Task 决定优先级）
- 不做安全扫描或依赖漏洞检查

## 验收标准

- [ ] 扫描报告完成并归档至 `docs/review/v3_compliance_scan.md`
- [ ] 报告包含：超限文件清单、裸 except 分类、类型标注率、print 残留清单
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/062-compliance-scan-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 7.3 跨切面规则合规扫描
- `AGENTS.md` — 规则 58, 64, 65, 67

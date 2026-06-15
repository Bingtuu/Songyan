# V3.x 阶段归档索引

> **归档日期**: 2026-06-07
> **归档原因**: V3.x 阶段已完成，进入 V4.0 "Context-on-Demand" 架构改造

---

## 归档内容总览

| 类别 | 数量 | 说明 |
|------|------|------|
| 验证报告 | 2 | Ch41-Ch50、Ch51-Ch70 真实 LLM 验证报告 |
| 任务交接 | 17 | Task 067~081 全部 DONE 报告 + 原始规格 |
| 验证数据 | 2 | Ch41-Ch50 (6.0M)、Ch51-Ch70 (23M) 含 DB + JSONL + Markdown 报告 |
| 技术方案 | 1 | V3.x 技术方案文档 |

---

## V3.x 阶段里程碑

### V3.0 — 稳定长跑（Task 052 ~ 066）

> **目标**: 不新增功能，修到 30 章稳定跑通。

| 阶段 | 目标 | 验证标准 | 状态 |
|------|------|---------|:----:|
| 058a | 监控与韧性基础设施 | `ChapterRunLog` + 指标收集 | ✅ |
| 058b | 30 章封闭验证生成 | 30 章 accepted，无中断 | ✅ |
| 058c | 上下文膨胀修复 + 字数控制 | 7 项关键修复 | ✅ |
| 058d | Revision 收敛性修复 | `new_issues_introduced` 检测 | ✅ |
| 059~060 | JSONL 诊断 + 字数阈值验证 | 诊断系统 + 120% 阈值 | ✅ |
| 061~062 | Ch2-Ch6 根因 + 端到端重跑 Ch31-Ch40 | 修复效果验证 | ✅ |
| 063~066 | Layer 3 基建 | RAG/LLM/Agent 重构 + 合规扫描 | ✅ |

### V3.1 — 质量跃迁（Task 067 ~ 073）

> **目标**: 上下文成本可控、Settlement 干净、Revision 收敛有保障。

| Task | 内容 | 交付 | 状态 |
|------|------|------|:----:|
| 067 | Genre Rules 按需加载 | 减少不必要规则注入 | ✅ |
| 068 | Writer Feedback 注入 | 上一轮 review 反馈回流 Writer | ✅ |
| 069a | 分层摘要 — 数据层与生成器 | ArcSummary / VolumeSummary + 生成器 | ✅ |
| 069b | 分层摘要 — 系统集成 | `load_layered_summaries()` + 自动触发 | ✅ |
| 070 | JSONL 诊断增强 | 诊断字段扩展 | ✅ |
| 071 | RAG 独立调试 | RAG 子系统可独立运行测试 | ✅ |
| 072 | Settlement source_quote 去噪 | 长度/内容/关键词/去重过滤 | ✅ |
| 073 | 截断重写策略 | 2 轮未收敛 → 整章重写 + avoid-list | ✅ |

### V3.1-EXT — 止血修复（Task 074 ~ 080）

> **目标**: 将稳定运行区间从 Ch30 延长到 Ch50+。

| Task | 内容 | 交付 | 状态 |
|------|------|------|:----:|
| 074 | 对话质量 Specialist | DialogueQualityAuditor（不阻塞） | ✅ |
| 075 | Checkpointer 抽象层 | `memory` / `sqlite` 工厂模式，根治 WAL 死锁 | ✅ |
| 076 | Writer 强制字数截断 | 阈值 1.3x→1.5x，下界保护 0.70x | ✅ |
| 077a | 分层 Setting 库 | 排序 + 入站过滤 + 关键词重叠 | ✅ |
| 077b | BudgetPruner 硬断言 | 核裁通道：逐级丢弃低优先级分区 | ✅ |
| 077c | Review 遗留修复 | 规格偏差修复 + 语义修正 + fallback 边界 | ✅ |
| 078 | 伏笔生命周期管理 | 逾期归档 + human_marks 时间窗口 | ✅ |
| 079 | RevisionHandler 重构 | 分段修订 + 保留率验证（>50%） | ✅ |
| 080 | 角色出场窗口 | Arc 窗口过滤 + minimal snapshot 策略 | ✅ |

### V3.1-VAL — 长程验证（Task 081 ~ 082）

| Task | 内容 | 结果 | 状态 |
|------|------|------|:----:|
| 081 | Ch51-Ch70 验证 | 19/20 章成功，budget_used 1.46 平均，Ch60 后再次恶化 | ✅ |
| 082 | Ch71-Ch100 验证 | — | ⏸️ 取消（转入 V4.0） |

---

## 验证关键结论

### Ch41-Ch50 验证

- **流程跑通率**: 100% (10/10)
- **budget_used max**: 2.02x
- **截断重写触发率**: ~30%（偏高）
- **连续性健康分**: 0.0 (Ch48) ❌

**核心问题暴露**:
1. 上下文静态基线持续增长（Ch50 `final_tokens=19175`，超预算 100%）
2. 字数控制系统性失效（Ch45-Ch50 达目标的 200-220%）
3. RevisionHandler 失效（`content_truncated`、`patch_not_found` 频发）
4. ContinuityAuditor 约束爆炸（Ch48 constraints_written=236）

### Ch51-Ch70 验证

- **19/20 章成功**（Ch51 因脚本崩溃缺失）
- **budget_used 趋势**:
  - Ch52-Ch59: 0.88-1.31（蜜月期）
  - Ch60-Ch63: 1.27-1.56（边际递减）
  - Ch64-Ch70: 1.85-2.32（恶化期，超 Ch50 基线）
- **字数达标率 (±20%)**: 42% (8/19)
- **连续性健康分**: 持续 2.0

**核心结论**:
> **076-080 修复将稳定区间从 Ch50 延长到 Ch60，但无法支撑到 Ch70。**
>
> 验证了"预组装上下文包"架构存在结构性天花板。仅靠 BudgetPruner 裁剪无法阻止静态基线上升，必须改为"Agent 按需检索上下文"的 Context-on-Demand 架构。

---

## 文件索引

```
archive/v3/
├── INDEX.md                          # 本文件
├── docs/
│   └── development-tech-plan-v3.md   # V3.x 技术方案
├── reports/
│   ├── v3.1_ch41_ch50_validation_report.md
│   └── v3.1_ch51_ch70_validation_report.md
├── tasks/
│   ├── 067-genre-rules-on-demand.md
│   ├── 068-writer-feedback-injection.md
│   ├── 069a-layered-summary-generators.md
│   ├── 069b-layered-summary-integration.md
│   ├── 070-jsonl-diagnostics-enhancement.md
│   ├── 071-rag-debugging.md
│   ├── 072-settlement-source-quote-denoising.md
│   ├── 073-truncation-rewrite-strategy.md
│   ├── 074-dialogue-quality-specialist-DONE.md
│   ├── 075-checkpointer-abstraction-DONE.md
│   ├── 076-writer-forced-truncation-DONE.md
│   ├── 077a-layered-setting-library-DONE.md
│   ├── 077b-budget-hard-enforcement-DONE.md
│   ├── 077c-review-fixes-DONE.md
│   ├── 078-foreshadowing-lifecycle-DONE.md
│   ├── 079-revision-handler-restructuring-DONE.md
│   ├── 080-character-appearance-window-DONE.md
│   └── 081-ch51-ch70-validation-DONE.md
└── tests/
    ├── validation_ch41_50/           # Ch41-Ch50 验证数据 (6.0M)
    │   ├── test.db
    │   ├── task_081_log.jsonl
    │   └── task_081_report.md
    └── validation_ch51_70/           # Ch51-Ch70 验证数据 (23M)
        ├── test.db
        ├── task_081_log.jsonl
        └── task_081_report.md
```

---

## V4.0 起点

V4.0 核心决策：**废弃"预组装"模式，改为"Agent 按需检索上下文"的 Context-on-Demand 架构。**

详细规划见 `C:\Users\mayn\.kimi\plans\wiccan-warpath-stature.md`（V4.0 技术规划文档）。

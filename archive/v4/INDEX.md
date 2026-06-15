# V4.0 归档索引

> **V4.0 代号**: Context-on-Demand 架构改造
> **时间范围**: 2026-05 ~ 2026-06
> **验证范围**: Ch1-Ch50（Task 099 81.6% 达标率）
> **归档日期**: 2026-06-13

---

## V4.0 核心目标

> **"废弃预组装上下文包，改为 Agent 按需检索上下文。支撑 100+ 章稳定生成。"**

实际交付：预组装上下文包在 V4.0 内部被充分优化（BudgetPruner、四信号系统、ContextPressure），验证到 Ch50 达标率 81.6%。ContextService 按需检索架构因 token budget 已优秀（1.073 平均）而暂缓，核心问题从"检索架构"转向"信息密度控制"。

---

## V4.0 关键成果

### Phase 1 — 基建与修复（Task 083~095）

| Task | 内容 | 关键交付 |
|------|------|---------|
| 083~087 | LifecycleScheduler 框架 | Schema + 生命周期管理 + 动态预算 |
| 088~090a | 字数硬约束 | Writer 1.20x/0.80x + RevisionHandler 1.25x/0.75x |
| 090b | Rewrite 护栏 | rewrite ±25% → ±20%，硬截断回退 |
| 091 | Phase B 收官验证 | Ch2-Ch70，69 章 0 失败 |
| 092~095 | 场景预算 + Health Score + 场景保护 | scene_budget prompt + 分类加权扣分 + 截断保场景 |

### Phase 2 — 验证与优化（Task 096~100c）

| Task | 内容 | 关键数据 |
|------|------|---------|
| 096 | Ch2-Ch50 回归验证 | 达标率 70.2%（基线）|
| 098 | 四信号系统 | 上下文压力计 + Accept 守卫 + Craft Card 1.0.9 |
| 099 | Ch2-Ch50 重跑验证 | **达标率 81.6%**（+11.4pp），0 失败 |
| 100a | RevisionHandler 下限保护 | MIN_CONTENT_RATIO 0.50→**0.85** |
| 100b | 流程质量门 | accept 前三联检（字数/保留率/新问题）|
| 100c | 上下文压力优化 | narrative_fullness 客观化，硬上限动态化 |

---

## V4.0 关键结论

1. **预组装上下文包可以被优化到 Ch50 级别**
   - BudgetPruner + focal_distance + 动态上限 + 四信号系统 = 81.6% 达标率
   - 不是"必须废弃"，而是"需要更聪明地控制加载什么"

2. **token budget 不是瓶颈**
   - Task 091: 平均 budget_used = 1.073，最大 1.291
   - ContextService 按需检索的原始动机（budget 爆炸）已被 BudgetPruner 缓解

3. **真正的瓶颈是信息密度**
   - 不是"加载太多"，而是"加载了不该加载的"
   - 角色档案、设定、伏笔的累积无法仅靠裁剪解决

4. **V4.0 → V5.0 的转向**
   - 原规划 Phase C（ContextService 按需检索）暂缓
   - 新方向：Context Diet 2.0（智能遗忘 + 分层压缩 + 活跃信息池控制）

---

## 归档文件

| 文件 | 说明 |
|------|------|
| `103-v4-0-docs-handover.md` | V4.0 Phase B 文档交接 + 决策门 1（未执行，归档）|
| `104-context-service-core.md` | ContextService 核心接口（暂缓，归档）|
| `105-context-service-integration.md` | ContextService 集成（暂缓，归档）|
| `106-context-service-regression.md` | ContextService 回归验证（暂缓，归档）|

---

## 参考

- `docs/STATUS.md` — 当前项目状态（V5.0）
- `AGENTS.md` — 开发代理指令（V5.0 规则）
- `archive/v3/INDEX.md` — V3.x 归档

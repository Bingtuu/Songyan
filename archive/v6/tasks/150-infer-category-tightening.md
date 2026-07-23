# Task 150: `_infer_setting_category` 收紧（critical 双命中 + 去硬编码主角名）

> **Phase**: V6 阶段 B（末端治理）
> **优先级**: P1（降低 critical 误判，直接支撑 T6b「P1 orphan=0」与 T6c 归因）
> **依赖**: 阶段 0（Task 142 项目大纲/主角信息）+ 阶段 A 度量落地；与 Task 149 独立可并行
> **预计工作量**: 小
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 B

---

## Goal

收紧 `_infer_setting_category` 的 `critical` 判定，去掉硬编码主角名，改读项目主角档案，使"世界观细节 / 背景设定被误判为 critical"显著减少——从而少产生 critical orphan（T6b）、并让 T6c 归因更干净（真 critical 才计入）。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- `_infer_setting_category`（`src/songyan/agents/settlement_extractor/_apply.py:688-719`）是纯关键词分类器，对 `f"{setting_key} {setting_name} {description}".lower()` 匹配：technical → critical → historical → 否则 `background`。
- **critical 判定已是"双命中"**：需同时命中 `critical_keywords`（主角/protagonist/命格/天赋/血脉/传承 …）**且** `protagonist_related`（`林渊`/主角/他/她/能力/状态/命运/目标 …）。问题不在"是否双命中"，而在：
  1. `protagonist_related` 里**硬编码了主角名 `林渊`**，换项目/换主角即失效或误伤；
  2. `protagonist_related` 含**过泛的通用词**（"他/她/能力/状态"），几乎任何句子都能命中第二个条件，等于把 critical 判定退化成"只要命中 critical_keywords 即 critical"。
  → 这正是 Task 138m「22 个世界观细节被误判 critical」的根因。
- 项目主角信息来源：Task 142 已让项目可携带大纲；主角档案在 `protagonist_profile`（硬约束上下文，AGENTS.md 已列为不裁剪项）。
- **主角名读取入口**：新增 `ProjectService.get_protagonist_names(project_id) -> set[str]`，从项目配置/大纲的 `protagonist_profile` 字段解析 `name` + `aliases`，供 `_update_continuity_tracking` 在调用 `_infer_setting_category` 前注入。若 `_apply.py` 为同步上下文，允许在 service 层预取后传入。
- **无主角信息保守回退策略**：`protagonist_names=None` 时，`critical` 判定仍要求命中 `critical_keywords`，但第二命中条件收缩为**不含通用代词的指涉词集**（如"主角/主人公/命定之人/全书核心"），避免把任意世界观细节判为 critical。该回退策略不得比现状更差（即不能引入更多 critical 误判）。

**边界**：这是"分类阈值收紧 + 去硬编码"，不是重写分类体系。保持 technical/critical/recurring/background/historical 五类不变（`category` 列 CHECK 依赖这些值）。

## In Scope（必须完成）

- [ ] **去硬编码主角名**：`protagonist_related` 不再写死 `林渊`；改为运行时读取项目主角名/别名（来自 `ProjectService.get_protagonist_names`）。无主角信息时按 **Context 中明确的保守回退策略** 分类（收缩为不含通用代词的指涉词集），行为确定且单测覆盖。
- [ ] **收紧第二命中条件**：把过泛通用词（他/她/能力/状态 等）从"判 critical 的充分条件"中剔除或降权，要求主角相关性由**主角名/别名/明确主角指涉**承载，而非任意代词。具体收紧规则可解释、可单测。
- [ ] **保持五类不变**：不新增/删除 category 取值；不改 CHECK。
- [ ] 遵守边界：分类函数仍是纯函数或仅依赖显式传入的主角信息；不新增 LLM 调用；无主角档案项目行为可回退且不劣化（至少不比现状更差）。

## Out of Scope（明确不做）

- 不做录入侧降级 / 候选态（Task 149）。
- 不做 MR 上限 / 排序（Task 151）。
- 不做 resolve/作废出口（Task 152）。
- 不引入 LLM 语义分类——保持关键词 + 主角档案的确定性规则。

## 接口契约

```python
# 由纯关键词函数演进为「显式接收主角标识」的分类；调用方在后处理注入主角名/别名
def _infer_setting_category(
    setting: NewSetting,
    *,
    protagonist_names: set[str] | None = None,  # None -> 保守回退
) -> str:
    """critical 需命中 critical_keywords 且命中 protagonist_names（而非通用代词）."""
```

（若最终选择在 service 层预取主角名再传入，签名以 DONE 为准；核心是**不再硬编码 `林渊`**。）

## 测试要求

### Layer 2: 模块测试
- [ ] **138m 回归样本**：构造 138m 中被误判 critical 的世界观细节样本（≥22 条的代表子集），验证收紧后 **≥20/22 不再判 critical**（判为 background/historical/recurring）。
- [ ] **真 critical 不漏**：主角能力/命格/血脉类真 critical 设定，在提供主角名时仍判 critical（避免收紧过头把真 critical 降级，反伤 continuity）。
- [ ] **去硬编码**：换一个主角名（非 `林渊`）的项目，主角相关 critical 仍能命中；`林渊` 不再被写死特权。
- [ ] **无主角信息回退**：`protagonist_names=None` 时按既定保守策略分类，行为确定；138m 误判样本 **≥15/22 不再判 critical**（严格优于现状），单测覆盖。

### Layer 3: 历史 DB 复算（可选，归因佐证）
- [ ] 用 138m/138n 数据复算：收紧后新判 critical 数下降，且 P1(critical) orphan 不升（配合 Task 149 一起看 T6b/T6c）。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_150_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] 138m 误判样本 ≥20/22 不再判 critical；真 critical 不漏判；主角名不再硬编码。
- [ ] 无主角信息时有明确且经单测的回退行为：`protagonist_names=None` 下，138m 的 22 个误判样本仍 **≥15/22 不再判 critical**（回退口径下限，弱于有主角名时的 ≥20/22，但必须严格优于现状——现状硬编码 `林渊` + 泛词几乎全判 critical）。
- [ ] 不违反不可违背规则：分类仍确定、无新增 Agent/LLM；不改 category 取值集合。
- [ ] 生成 `archive/v6/tasks/150-infer-category-tightening-DONE.md`，含收紧规则、138m 样本命中率、主角名读取方式与回退策略。
- [ ] 更新 `tasks/V6-README.md`（150 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.4-T6、§3 阶段 B（Task 150 行）
- 现有代码：`settlement_extractor/_apply.py:688-719`（`_infer_setting_category`）及其调用方 `_update_continuity_tracking`
- 138m 根因报告：`archive/v5/reports/task-138m-critical-orphan-root-cause-report.md`
- 主角档案来源：Task 142 项目大纲导入 / `protagonist_profile` 硬约束

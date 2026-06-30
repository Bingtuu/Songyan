# Task 138n：QG 阻断式 Critical Orphan Revision + Mandatory Reference 上限调优

> **类型**: 工程实现 / 验证
> **状态**: 已完成（代码实现 + Ch1-Ch30 重跑验证通过）
> **前置**: Task 138m 已完成，推荐方案为 **A + C**（QG 阻断式 revision + Context Diet 上限调优）。
> **依赖**: Task 138h-138j（强制回收闭环已落地）、Task 138k/138l（长窗口 rehearsal 数据已收集）。
>
> **代码/单测状态**: 已实现 A1/A2/A3/C1/C2/C3，新增 `tests/test_task138n_mandatory_reference_revision.py`，全量 pytest 2021 passed / 1 xfailed / ruff 通过。
>
> **重跑结果**: Run `run-ba25db19`，DB `.tmp/task138n_ch1_ch30_rerun.db`；Ch30 health **8.5**，orphaned **25**（全部为 P3），**P1/P2 critical orphan 0**；29/30 章节 settlement/QG 通过，仅 Ch13 未通过。
>
> **Ch13 根因**: 不是 settlement 失败或 MR 缺失，而是 3 轮 revision 后 quality gate 仍无法收敛，structural rewrite（v-13-4）因缺少结尾钩子失败，系统回滚到 rev-13-3 做降级接受（`quality_gate_passed=False`）。该章节 `mandatory_reference_issue_count=0`，与 A+C 改动无直接因果关系，判定为随机波动。报告见 `docs/reports/task-138n-ch1-ch30-rerun-report.md`。
>
> **合并状态**: 本任务中的 A+C 代码改动（ReviewMerger MR 聚合、RevisionHandler MR 专用 patch、MR 上限与排序、human_mark 预算对齐、critical 分类收紧）已作为 V5.2 主干默认配置在当前工作树生效。
>
> **归档说明**: Task 138m 根因分析中间数据（JSON/Markdown/脚本）已归档至 `archive/v5/138m-analysis/`；`.tmp/` 仅保留 138k/138n 关键 DB 与 metrics，历史 Ch10 focus DB 与临时脚本已清理。

## 目标

将 Task 138k Ch1-Ch30 rehearsal 中暴露的 35 个 P1 critical orphan 在下一轮 Ch1-Ch30 重跑中显著压降，分阶段验收：

- **阶段 1（Ch10-Ch20 小窗口）**：验证 MR 专用 patch 一轮修复率 ≥ 60%，MR 上限不引入新 orphan。
- **阶段 2（Ch21-Ch30）**：验证 P1 critical orphan 增量 ≤ 5，health 不继续下滑。
- **阶段 3（Ch1-Ch30 全量）**：目标 P1 ≤ 15、health ≥ 4.0；若未达标，按 fallback 引入 B 路径或进一步收紧 C3。

通过以下两条路径同时发力：

1. **A 路径（执行闭环）**：让 `mandatory_reference_missing` 真正进入 RevisionHandler 并走专用 patch，而不是被 ReviewMerger 的 5-issue 上限截断后用通用 patch 敷衍。
2. **C 路径（过载控制）**：给 `mandatory_references` 和 continuity human_mark 设置与章节阶段/场景数匹配的上限，避免 43 条强制约束同时砸向 Writer。

## 验收标准

- [ ] `review_merger._convert_rule_to_issues` 对 `mandatory_reference_missing` 的处理不再受 `max_rule_issues=5` 截断；采用**聚合 issue** 或**单独预算**方案，确保一次 revision 能看到全部（或 Top-N）缺失设定。
- [ ] `RevisionHandler` 新增针对 `mandatory_reference_missing` 的轻量 patch 路径：只补充缺失设定的提及/呼应，不整章重写；最多 2 轮；若仍缺失，按现有 safe-best / degraded_accept 路由处理。
- [ ] `_load_critical_mandatory_references` 增加每章上限（建议初始 `max_mandatory_references = min(scenes_count * 2, 12)`，并按 `silent_chapters` 降序、`introduced_in_chapter` 升序排序），仅注入最紧急的 N 条；上限为可配置参数，便于小窗口调参。
- [ ] `MAX_ORPHANED` / `max_constraints_per_chapter` / `max_marks_in_context` 与 MR 上限对齐：
  - `MAX_ORPHANED` 提高至与 MR 上限同量级（如 12），确保 MR 列表中的设定大多能拿到 human_mark；
  - `max_constraints_per_chapter` 提高至 24-30；
  - `webnovel_intense` 的 `human_memory.max_marks_in_context` 提高至 12（或在过滤逻辑中优先保留 MR 对应的 continuity mark）。
- [ ] `_infer_setting_category` 收紧 critical 判定：从“命中 `核心/锚/anchor/core`”改为“命中关键词 **且** 与主角/主线状态强相关”；作为推荐项执行，单独小窗口验证不误杀。
- [ ] 新增或更新单测覆盖：
  - MR 上限排序逻辑（含 `silent_chapters` 同分时的 `introduced_in_chapter` 次序）；
  - ReviewMerger 对大量 MR 缺失的聚合/预算行为；
  - MR 专用 patch 的修复率（构造 10 个缺失，patch 后 `mandatory_reference_check_passed=True`）；
  - patch 不整章重写（内容保留率 ≥ 0.85）。
- [ ] 执行阶段 1/2/3 验证，输出 `docs/reports/task-138n-qg-mandatory-reference-revision-loop-report.md`。

## 实现思路

### A1：解除 ReviewMerger 对 MR 缺失的 5-issue 上限

**位置**: `src/songyan/workflows/review_merger.py:215-232` 与 `:423-425`

当前 `_convert_rule_to_issues` 已经把 MR 缺失转成 critical issue 并放在最前面，但最后的统一 cap=5 会截断。如果 Ch30 有 38 个缺失，RevisionHandler 只能看到 5 个。

**推荐方案**：把 MR 缺失聚合成 **1 个 critical patch issue**，把全部缺失 setting_key 列表放入 `evidence_quote` / `issue_description`。

```python
if not rule_result.mandatory_reference_check_passed:
    missing_keys = rule_result.mandatory_reference_issues  # list[str]
    issues.append(
        ReviewIssue(
            issue_id=f"rule-mr-{version_id}",
            category=ReviewCategory.WORLD_CONSISTENCY,
            severity="critical",
            evidence_quote="; ".join(missing_keys[:30]),  # 上限 30 条，避免 prompt 爆炸
            evidence_location="全章",
            issue_description=f"本章缺失 {len(missing_keys)} 个 critical 设定的回收：{missing_keys[:10]}",
            expected="正文中应通过角色行动、对话、环境描写或剧情事件明确回收上述设定。",
            actual="正文中未找到上述设定的明确提及。",
            suggested_fix="在合适位置为每个缺失设定插入一处自然提及，不要删除或重写已有正文。",
            fix_type="patch",
            confidence=1.0,
        )
    )
```

> 若聚合后证据文本过长，可先取 Top-N（N = 当前 MR 上限），保证 RevisionHandler 一轮能处理完。

### A2：RevisionHandler MR 专用 patch 路径

**位置**: `src/songyan/agents/revision_handler/__init__.py`（新增函数），并在 `run_revision` 中路由。

当 `patchable_issues` 中存在 `issue_id.startswith("rule-mr-")` 时，提取 missing_keys，调用专用 patch：

```python
async def _patch_mandatory_reference_missing(
    content: str,
    missing_refs: list[dict],
    word_count_target: int,
) -> tuple[str, list[str]]:
    """为缺失的 mandatory reference 插入自然提及，返回修订后正文与已修复 key 列表。"""
    prompt = (
        "你是小说编辑。以下章节缺少一些前文的 critical 设定回收。"
        "请在保持原有叙事、不删除已有内容的前提下，为每个设定在合适位置插入一处自然提及。\n\n"
        "要求：\n"
        "1. 只能通过角色对话、环境细节、动作触发或剧情事件来提及，禁止直接罗列设定。\n"
        "2. 不要新增大段解释，每处提及 1-2 句话即可。\n"
        "3. 不要改变本章主要情节走向。\n"
        "4. 输出完整修订后的正文，不要添加解释、总结或 markdown 代码块。\n\n"
        f"缺失设定：{[r['setting_key'] for r in missing_refs]}\n\n"
        f"正文：\n{content}"
    )
    llm_response = await call_llm(prompt, temperature=0.3)
    from songyan.agents.writer import _extract_body
    revised = _extract_body(llm_response) or content
    # 简单校验哪些 key 已出现
    fixed = [
        r["setting_key"] for r in missing_refs
        if r["setting_key"].split(".")[-1].lower() in revised.lower()
        or str(r["setting_name"]).lower() in revised.lower()
    ]
    return revised, fixed
```

在 `run_revision` 中：

```python
mr_issues = [i for i in patchable_issues if i.issue_id.startswith("rule-mr-")]
other_issues = [i for i in patchable_issues if not i.issue_id.startswith("rule-mr-")]

if mr_issues:
    revised_for_mr, fixed_keys = await _patch_mandatory_reference_missing(
        content, missing_refs_from_issue(mr_issues[0]), word_count_target
    )
    # 字数保护
    if len(revised_for_mr) >= len(content) * MIN_CONTENT_RATIO:
        content = revised_for_mr
        # 标记已修复
        ...
```

> 若同时存在其他 patchable issues，先处理 MR patch，再处理其他 issues（或合并到 segmented revision）。优先保证 MR 闭环，因为 MR 缺失直接影响 continuity health。

### A3：RuleAuditor 与 gate_mode 的兼容

**位置**: `src/songyan/workflows/_nodes.py:rule_auditor_node`

- `observe` 模式下保持当前行为：记录但不阻断，后续靠 RevisionHandler 闭环。
- `enforce` 模式下，若 `mandatory_reference_missing` 聚合 issue 存在，可作为硬 fail 进入 `quality_gate_node`；但默认 `observe` 已足够，因此 **A 路径核心在 A1/A2，不在 enforce 阻断**。

### C1：Mandatory reference 上限与排序

**位置**: `src/songyan/workflows/_helpers.py:_load_critical_mandatory_references`

修改后：

```python
async def _load_critical_mandatory_references(
    project_id: str,
    chapter_number: int,
    scenes_count: int = 3,
    max_mandatory_references: int | None = None,
) -> list[dict]:
    ...
    # 默认上限：每场景 2 条，但不超过 12
    if max_mandatory_references is None:
        max_mandatory_references = min(max(scenes_count * 2, 6), 12)

    # 排序：先最紧急（沉寂章数高），同分则越早引入的越优先
    result.sort(
        key=lambda r: (r["silent_chapters"], -r["introduced_in_chapter"]),
        reverse=True,
    )
    if len(result) > max_mandatory_references:
        dropped = result[max_mandatory_references:]
        result = result[:max_mandatory_references]
        logger.info(
            "task138n.mandatory_references_truncated",
            project_id=project_id,
            chapter_number=chapter_number,
            kept=max_mandatory_references,
            dropped_keys=[r["setting_key"] for r in dropped],
        )
    return result
```

调用点（`context_manager` 组装时）需要传入当前章的 `scenes_count`（可取 `chapter_goal` 或 creative_brief 的 scene target，默认 3）。

### C2：Continuity human_mark 预算匹配

**位置**: `src/songyan/agents/continuity_auditor/_constraints.py`

- `MAX_ORPHANED` 从 8 提高到 **12**（与 MR 上限对齐）。
- `max_constraints_per_chapter` 从 20 提高到 **24**。
- 生成约束时优先保证 critical orphan 全部进入候选，再分配 recurring/background 预算。

**位置**: `creative_modes/webnovel_intense.json`

- `human_memory.max_marks_in_context` 从 10 提高到 **12**。
- 或在 `context_manager` 过滤逻辑中优先保留 source=continuity_auditor 且 target_key 在 MR 列表中的 mark。

### C3：Critical 分类启发式收紧（推荐项）

**位置**: `src/songyan/agents/settlement_extractor/_apply.py:_infer_setting_category`

当前 critical 关键词：`主角、核心、能力、锚、法则、本源、命格、天赋、血脉、传承、main、protagonist、core、anchor`。

改为：

```python
critical_keywords = [
    "主角", "protagonist", "main",
    "命格", "天赋", "血脉", "传承",
]
# 必须同时与主角/主线状态相关
protagonist_related = [
    "林渊", "主角", "他", "她", "能力", "状态", "命运", "目标",
]
if any(kw in text for kw in critical_keywords) and any(kw in text for kw in protagonist_related):
    return "critical"
```

> 该改动会改变 P1 基数，必须单独跑 Ch1-Ch10 小窗口验证，确认不会把真正 critical 的设定误判为 background。

## 验证计划

1. **单元/集成测试**：本地跑 `pytest tests/ -q` 和 `ruff check src/ tests/`，确保无回归。
2. **MR patch 修复率单测**：构造 10 个 synthetic MR 缺失，调用 `_patch_mandatory_reference_missing`，断言修复后 `run_rule_audit(...).mandatory_reference_check_passed` 为 True，且内容保留率 ≥ 0.85。
3. **Ch10-Ch20 小窗口实跑**：使用与 Task 138k 相同的 genre/mode/project seed，观察：
   - 每章 MR 数量是否符合上限；
   - MR patch 一轮修复率；
   - revision 轮数、运行时长、P1 orphan 趋势。
4. **Ch21-Ch30 验证**：重点观察新增 critical orphan 速率是否下降。
5. **Ch1-Ch30 全量重跑**：复现 Task 138k 配置，对比 Ch30 P1 orphan 与 health。
6. **报告**：输出 `docs/reports/task-138n-qg-mandatory-reference-revision-loop-report.md`，记录改动点、测试结论、最终指标与未达标时的 fallback 决策。

## Fallback 与风险

- **主要风险**：MR patch 一轮修复率不足 60%，导致 revision 轮数增加、运行时间变长。
- **Fallback 1**：若阶段 1 修复率不足，改用 **B 路径**（CreativeDirector 在 brief 阶段预分配回收场景）。
- **Fallback 2**：若阶段 2 P1 仍增长，优先执行 **C3** 并进一步收紧 critical 判定。
- **Fallback 3**：若阶段 3 仍未达到 P1 ≤15 / health ≥4.0，接受 P1 ≤20 / health ≥3.5 作为 V5.2 中期基线，进入 Ch50+  rehearsal 后再评估。

## 不做的事

- 不引入新 Agent 类型（保持 Writer/RevisionHandler/RuleAuditor 边界）。
- 不修改 SettlementExtractor 的角色/数值提取逻辑（与当前 P1 orphan 根因无关）。
- 不扩大 rehearsal 到 Ch50+，直到 Ch1-Ch30 指标达标或 fallback 明确。

## 参考

- Task 138m 决策报告：`docs/reports/task-138m-critical-orphan-root-cause-report.md`
- Task 138k 长窗口报告：`docs/reports/task-138k-long-window-rehearsal-report.md`
- Task 138h 强制回收闭环：`tasks/138h-critical-orphan-mandatory-recall-loop-DONE.md`
- 关键代码：
  - `src/songyan/workflows/_helpers.py:_load_critical_mandatory_references`
  - `src/songyan/workflows/review_merger.py:_convert_rule_to_issues`
  - `src/songyan/agents/revision_handler/__init__.py:run_revision`
  - `src/songyan/agents/continuity_auditor/_constraints.py`
  - `src/songyan/agents/settlement_extractor/_apply.py:_infer_setting_category`

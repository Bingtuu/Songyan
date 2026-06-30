# Task 138j: Writer Mandatory Reference Recycle Hints（Writer 强制回收约束附加具体回收提示）

> **类型**: Prompt 调优 / 认知负荷降低
> **状态**: 已完成
> **前置**: Task 138i（措辞硬化）完成后执行；或 138i 效果有限时提前启动
>
> **边界**: 不改 Review/Settlement/Continuity 逻辑；只改 mandatory_references 的数据组装和 prompt 渲染

## 背景

Task 138h 子项 A+B 建立了"注入 + 检测"双层闭环，但 `run-a225b713` 证明 RevisionHandler 无法补救 Writer 初稿中的设定缺失。Task 138i 尝试通过 prompt 措辞硬化在源头提升 Writer 服从性。

如果 138i 的措辞硬化将回收率提升到 `≥2/5` 但仍未达标（`≥4/5`），说明 Writer 的**认知负荷**是瓶颈：Writer 知道要回收 5 个设定，但不知道如何自然地将它们融入当前场景，导致选择性忽略。

本任务通过为每个 mandatory_reference **附加具体回收提示**（recycle hint），降低 Writer 的"执行犹豫"，将回收率从基线提升到 `≥4/5`。

## 目标

在 `mandatory_references` 中增加 `recycle_hint` 字段，为 Writer 提供"怎么回收"的具体建议，将初稿回收率从基线提升到 `≥4/5`，最终达成 `health ≥5.0`。

## 不做的事

- **不修改 RuleAuditor、RevisionHandler、review_merger 的检测/修复逻辑**（Task 138h 子项 B 已足够）。
- **不修改 `ORPHANED_THRESHOLDS`**。
- **不新增 setting alias**（alias 问题已在 138g 解决）。
- **不动 settlement evidence gate**（已稳定）。
- **不引入新的 Agent 或 Workflow 节点**。

## 要做的事

### 1. 在 `_load_critical_mandatory_references` 中附加 `recycle_hint`

修改 `src/songyan/workflows/_helpers.py` 中的 `_load_critical_mandatory_references` 函数：

```python
async def _load_critical_mandatory_references(...) -> list[dict]:
    ...
    for row in rows:
        ...
        # 根据 setting_key 的最后一个 segment 推断回收提示
        key_alias = str(row.get("setting_key") or "").split(".")[-1]
        recycle_hint = _infer_recycle_hint(key_alias)
        result.append(
            {
                "setting_key": ...,
                "setting_name": ...,
                "category": "critical",
                "silent_chapters": silent,
                "introduced_in_chapter": ...,
                "last_mentioned_chapter": last_mentioned,
                "recycle_hint": recycle_hint,  # <-- 新增
            }
        )
```

新增函数 `_infer_recycle_hint(key_alias: str) -> str`：

```python
_RECYCLE_HINTS: dict[str, str] = {
    "surface_material": "可通过环境描写（触感、视觉观察）、角色对话提及材料特性、或与其他材质对比来回收",
    "phase_flush_mechanism": "可通过角色讨论技术原理、剧情中触发/关闭机制、或发现机制残留痕迹来回收",
    "team_7": "可通过角色对话回忆团队行动、提及团队成员、或发现团队遗留痕迹来回收",
    # 兜底：基于 key_alias 的通用提示
}

def _infer_recycle_hint(key_alias: str) -> str:
    return _RECYCLE_HINTS.get(
        key_alias,
        "可通过角色对话回顾、环境细节呼应、或剧情事件直接触发来回收",
    )
```

**设计原则**：
- 提示是**建议性**的，不强制 Writer 必须按提示执行。
- 提示覆盖最常见的回收场景（环境描写、角色对话、剧情事件）。
- 不硬编码所有 setting_key，只覆盖历史高频 orphan；其他 setting 使用兜底提示。
- 提示文本简短（<40 字），避免增加 prompt 长度负担。

### 2. 在 Writer prompt 中渲染 `recycle_hint`

修改 `agents/writer.py` 中的 `_render_prompt`，在 `mandatory_references_text` 中追加 `recycle_hint`：

```python
for ref in ctx.mandatory_references:
    name = ref.get("setting_name") or ref.get("setting_key") or "未命名设定"
    key = ref.get("setting_key") or ""
    silent = ref.get("silent_chapters", 0)
    hint = ref.get("recycle_hint", "")
    hint_line = f"  【建议】{hint}" if hint else ""
    lines.append(f"- {name}（{key}）：已沉寂 {silent} 章{hint_line}")
```

渲染效果示例：

```
- 巨型遗迹表面材料特性（artifact.mega_ruin.surface_material）：已沉寂 9 章
  【建议】可通过环境描写（触感、视觉观察）、角色对话提及材料特性、或与其他材质对比来回收
- 相位冲刷机制（artifact.ruin.phase_flush_mechanism）：已沉寂 5 章
  【建议】可通过角色讨论技术原理、剧情中触发/关闭机制、或发现机制残留痕迹来回收
```

### 3. 同步更新 prompt 模板

修改 `prompts/cards/writer/1.1.0.yaml` 和 `1.2.0.yaml`：
- 在 `variables` 列表中确认 `mandatory_references` 已存在（Task 138h 子项 A 已完成）。
- 无需新增变量，因为 `recycle_hint` 已在 `mandatory_references_text` 的渲染逻辑中嵌入。

## 实施顺序

1. 修改 `_load_critical_mandatory_references` 附加 `recycle_hint`。
2. 修改 `agents/writer.py` 渲染逻辑包含 `recycle_hint`。
3. 运行 `ruff check src/ tests/`。
4. 运行新增单测（覆盖 `_infer_recycle_hint` 和渲染逻辑）。
5. 复跑 Ch10-Ch12（使用新的 `.tmp` 副本 DB）。
6. 分析 Writer 初稿 `v-12-1` 中 mandatory_reference 回收率。

## 验收标准

### 代码层

- `ruff check src/ tests/` 通过。
- 新增单测覆盖：
  - `_infer_recycle_hint` 对已知 key_alias 返回正确提示。
  - `_infer_recycle_hint` 对未知 key_alias 返回兜底提示。
  - `mandatory_references_text` 渲染包含 `recycle_hint`。
- 全量 pytest 不引入 regression。

### 实跑层

- 使用新的 `.tmp` 副本 DB 复跑 Ch10-Ch12。
- Ch11/Ch12 settlement、summary、QG 全部通过。
- **核心指标**：Writer 初稿 `v-12-1` 中，5 个 critical mandatory_reference 至少回收 **4 个**（回收率 ≥4/5）。
- **出口指标**：Ch12 continuity `health ≥5.0` 且 `critical orphan ≤1`。
- **连续两次复跑出口**：两次均达成上述指标，证明闭环稳定。

### 文档层

- 本文件更新实施记录和结论。
- `STATUS.md`、`V5-README.md` 同步更新。

## 技术细节备忘

- `_infer_recycle_hint` 的 `_RECYCLE_HINTS` 字典是**可扩展的**：后续发现新的高频 orphan 时，只需追加键值对即可。
- `recycle_hint` 只影响 Writer prompt，不影响 ContextPackage 的其他消费方（如 RuleAuditor 只检查 `setting_key`/`setting_name`，不检查 `recycle_hint`）。
- 复跑前执行预检：确认无残留 Python 进程、主库 Ch1-Ch10 全部 accepted。

---

## 实施记录

- **完成时间**: 2026-06-29
- **修改文件**:
  - `src/songyan/workflows/_helpers.py`: 新增 `_RECYCLE_HINTS` 字典 + `_infer_recycle_hint()` 函数；`_load_critical_mandatory_references()` 返回结果附加 `recycle_hint`
  - `src/songyan/agents/writer.py`: `_render_prompt` 渲染 `recycle_hint` 为 "【建议】..."
  - `tests/test_task137_setting_recycling.py`: 追加 `TestTask138jRecycleHints`（4 个测试）
- **复跑结果** (`run-0b35ae60`):
  - Ch12 health=3.9, orphaned=14（baseline health=3.0, orphaned=14）
  - P1 critical orphan: 5 → **2**（改善 60%）
  - Writer 初稿 mandatory_reference 回收率: 0/5 → **3/5**
- **结论**: `recycle_hint` **显著有效**。为 Writer 提供具体回收路径后，critical orphan 大幅压缩。但未达最终验收标准（health ≥5.0, critical orphan ≤1）。P3（background/technical orphan=14）是 health 无法突破 5.0 的主因。
- **后续方向**: 接受当前边界作为阶段性成果。后续通过长窗口 rehearsal 观察 natural decay 趋势。

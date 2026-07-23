# Task 138i: Writer Prompt Mandatory Reference Tone Hardening（Writer 强制回收约束措辞硬化）

> **类型**: Prompt 调优 / 软约束硬化
> **状态**: 已完成（效果有限）
> **前置**: Task 138h 子项 A 已完成；`run-a225b713` 证明 Writer 在收到 mandatory_references 列表后仍选择忽略 5/7 项
>
> **边界**: 不改代码，只改 Writer prompt 模板中的文本措辞

## 背景

Task 138h 子项 A 已在 Writer prompt 中注入 `mandatory_references` 硬约束块，子项 B 已在 RuleAuditor 中建立 `mandatory_reference_missing` 检测规则。但 `run-a225b713` 实跑证据显示：

- Writer 初稿 `v-12-1-c433ff48` 对 5 个 critical mandatory_reference 完全零提及。
- RevisionHandler 的 patch 无法补救（`rev-12-2-8ef83f5a` 仍 5/5 缺失，且因字数膨胀被 abandoned）。
- 最终 accepted 的是有缺陷的初稿，Ch12 continuity 仍为 `health=3.0`、`orphaned=14`。

核心判断：**RevisionHandler 只做 patch，不整章重写**。如果 Writer 初稿中完全没有提及某个设定，patch 很难在不破坏叙事的情况下将其插入。因此，必须在 Writer 生成阶段就从源头解决问题。

当前 prompt 中的 mandatory_references 段落措辞偏陈述式（"Writer 必须在正文中..."），对 LLM 的服从性不足。本任务通过**措辞硬化**（指令式 + 心理锚定 + 否定式强化）来提升 Writer 的执行率。

## 目标

通过最低复杂度的方式（只改 prompt 文本），将 Writer 对 mandatory_references 的初稿回收率从 `0/5` 提升到 `≥2/5`。

## 不做的事

- **不修改任何 Python 代码**（包括 RuleAuditor、RevisionHandler、ContextManager、review_merger 等）。
- **不新增 setting alias**。
- **不修改 `ORPHANED_THRESHOLDS`**。
- **不改动 settlement / continuity / QG 任何逻辑**。
- **不引入新的 prompt 变量或模板结构**（只改现有 `mandatory_references` 段落的文字内容）。

## 要做的事

### 修改 Writer prompt 中的 mandatory_references 执行要求段落

当前 `prompts/cards/writer/1.1.0.yaml` 和 `1.2.0.yaml` 中的 mandatory_references 段落（Task 138h 子项 A 已添加）：

```jinja2
{% if mandatory_references != "（无）" %}
## 强制连续性约束（必须回收 — P1 级别）
{{ mandatory_references }}

**执行要求**：以上列出的 critical 设定不是建议，而是强制约束。Writer 必须在正文中通过角色行动、对话、环境描写或剧情事件明确回收每一项；若因剧情发展确实无法回收（如设定所在场景已物理损毁），必须在正文中用至少一句话给出剧情豁免原因。
{% endif %}
```

**改为**（核心变化：从陈述式改为指令式 + 否定式心理锚定）：

```jinja2
{% if mandatory_references != "（无）" %}
## 强制连续性约束（必须回收 — P1 级别）
{{ mandatory_references }}

**执行要求**：
1. 以上列出的 critical 设定不是建议，而是强制约束。
2. 在构思本章情节时，你必须为每个列出的设定安排至少一处明确的提及、使用或呼应。
3. **不要跳过任何一个设定**——如果某个设定与当前场景的自然走向不符，请微调场景走向，让设定有机融入（如通过角色对话回顾、环境细节呼应、或剧情事件直接触发）。
4. 若因剧情发展确实无法回收（如设定所在场景已物理损毁），必须在正文中用至少一句话给出剧情豁免原因。
5. 完成正文后，快速自检：确认上述列表中的每个设定都在本章正文中出现了至少一次。若有遗漏，立即补充。
{% endif %}
```

**措辞设计原理**：
- **"不要跳过任何一个设定"**：否定式指令对 LLM 的约束力强于肯定式。
- **"请微调场景走向"**：给出具体行动路径，降低 Writer 的"执行犹豫"。
- **"快速自检"**：在生成流程末尾增加元认知检查点，利用 LLM 的自检倾向提升遗漏检出率。
- **整体从"建议性语言"转向"命令性语言"**，减少 LLM 将其视为可选项的概率。

## 实施顺序

1. 修改 `prompts/cards/writer/1.1.0.yaml` 中的 mandatory_references 段落。
2. 同步修改 `prompts/cards/writer/1.2.0.yaml`（保持两个版本一致）。
3. 运行 `ruff check src/ tests/`（确认无 regression，虽然只改 yaml，但需确认 writer.py 渲染逻辑无需调整）。
4. 复跑 Ch10-Ch12（使用新的 `.tmp` 副本 DB）。
5. 分析 Writer 初稿 `v-12-1` 中 mandatory_reference 回收率。

## 验收标准

### 代码层

- `ruff check src/ tests/` 通过。
- 全量 pytest 不引入 regression。

### 实跑层

- 使用新的 `.tmp` 副本 DB 复跑 Ch10-Ch12。
- Ch11/Ch12 settlement、summary、QG 全部通过（保持基线）。
- **核心指标**：Writer 初稿 `v-12-1` 中，5 个 critical mandatory_reference 至少回收 **2 个**（回收率 ≥2/5）。
- 若达成 ≥2/5，本任务通过，进入 Task 138j（叠加回收建议）。
- 若仍为 0/5 或 1/5，说明 prompt 措辞对该模型已触及天花板，本任务标记为"效果有限"，证据沉淀后进入 Task 138j。

### 文档层

- 本文件更新实施记录和结论。
- `STATUS.md`、`V5-README.md` 同步更新。

## 技术细节备忘

- Prompt 渲染逻辑已由 Task 138h 子项 A 完成，无需改动 `agents/writer.py`。
- 两个 yaml 文件必须保持同步，因为 `run_137_ch10_focus_validation.py` 会临时将 default_version 切换到 1.2.0。
- 复跑前执行预检：确认无残留 Python 进程、主库 Ch1-Ch10 全部 accepted。

---

## 实施记录

- **完成时间**: 2026-06-29
- **修改文件**:
  - `prompts/cards/writer/1.1.0.yaml`: mandatory_references 段落措辞硬化
  - `prompts/cards/writer/1.2.0.yaml`: 同步修改
- **复跑结果** (`run-c8abacc8`): Ch12 health=3.0, orphaned=16（比 baseline 14 更差）。Writer 初稿 v-12-1 对 7/7 mandatory_references 零提及。
- **结论**: Prompt 措辞从陈述式改为指令式 + 否定式心理锚定 + 自检环节，对该模型（deepseek-chat）**没有任何改善效果**。Writer 仍基于场景自然性选择忽略与当前情节关联度低的设定。标记为"效果有限"，未达验收标准（回收率 ≥2/5）。

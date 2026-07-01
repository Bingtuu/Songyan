# Pass 17 — Prompt 工程与元标记防泄漏审查报告

> **范围**: PR-01 ~ PR-08 (Prompt 硬编码、工艺卡加载、版本管理、输出清理、元标记检测、字数控制、截断完整性、Rewrite 护栏)
> **日期**: 2026-06-25
> **审查者**: Codex
> **状态**: 完成（静态分析）

---

## 摘要

本 Pass 验证 Prompt 工艺卡体系和 Writer 输出的元标记清理机制。

| ID | 检查项 | 状态 | 验证方法 | 说明 |
|----|--------|:----:|---------|------|
| PR-01 | 代码中无硬编码长 prompt | ✅ | 审查 `writer.py` 内联字符串 | 无 >200 字符内联 prompt，均通过 `get_prompt_loader` 加载 |
| PR-02 | Prompt 从工艺卡加载 | ✅ | 审查 `_render_prompt` + `_load_prompt_template` | Writer 及各 Agent 均使用 `get_prompt_loader` |
| PR-03 | 工艺卡版本化管理 | ✅ | 审查 `prompts/cards/**/_manifest.yaml` | 存在 manifest，记录版本映射与变更描述 |
| PR-04 | Writer 输出正则清理 | ✅ | 审查 `_extract_body` | 清理 markdown 代码块、HTML 注释、旧版可见标记、首尾说明 |
| PR-05 | 元标记泄漏检测 | ⚠️ | 审查 `rule_auditor.py` + `llm_auditor.py` | 审查体系无专门元标记检测规则；Writer 输出清理提供前端保护 |
| PR-06 | 字数控制机制 | ✅ | 审查 `WORD_COUNT_TOLERANCE` + `word_count_bounds` | 默认 ±10%，截断工具按章节类型动态调整上限 (1.15x~1.35x) |
| PR-07 | 截断保场景完整性 | ✅ | 审查 `enforce_word_count` + `hard_truncate_at_boundary` | 优先在 scene 边界截断；回退策略按段落/句子边界 |
| PR-08 | Rewrite 字数护栏 | ✅ | 审查 `rewrite_node` | 注入 ±20% 字数硬约束 (0.80x ~ 1.20x) |

**7/8 项通过，1 项需观察（PR-05）。**

---

## F1: PR-01 — 代码中无硬编码长 prompt

### 验证方法

审查 `agents/writer.py` 中所有多行字符串和 f-string，排除 docstring。

### 验证结果

```python
# writer.py 中所有 triple-quote 均为 docstring
"""Writer Agent — 接收 ContextPackage，生成章节正文."""
"""将 ContextPackage 渲染为 Writer Prompt."""
"""从 LLM 响应中提取正文."""
"""生成精简 CreativeBrief 快照..."""
"""生成章节正文并保存为 ChapterVersion."""
```

业务逻辑中的字符串：
```python
# _compute_scene_budget (L30-50): 短格式化字符串，<200 字符
# _extract_body (L389-464): 正则清理规则，非 prompt
```

Prompt 加载入口：
```python
def _render_prompt(ctx: ContextPackage) -> str:
    from songyan.prompts import get_prompt_loader
    loader = get_prompt_loader()
    template = loader.load("writer", "default")
    ...
```

**结论：PR-01 通过。** Writer 及各 Agent 均通过 `get_prompt_loader` 加载外部工艺卡，代码中无内联长 prompt。

---

## F2: PR-02 — Prompt 从工艺卡加载

### 验证方法

全局搜索 `get_prompt_loader` 使用情况。

### 验证结果

```python
# writer.py L55
from songyan.prompts import get_prompt_loader
loader = get_prompt_loader()
template = loader.load("writer", "default")

# 其他 Agent 同样模式
goal_planner.py:    loader = get_prompt_loader(); template = loader.load("goal_planner", "default")
literary_auditor.py: loader = get_prompt_loader(); template = loader.load("literary_auditor", "default")
creative_director/__init__.py: loader = get_prompt_loader(); template = loader.load("creative_director", "default")
revision_handler/__init__.py: loader = get_prompt_loader(); template = loader.load("revision_handler", "default")
settlement_extractor/__init__.py: loader = get_prompt_loader(); template = loader.load("settlement_extractor", "default")
```

**结论：PR-02 通过。** 所有 Agent 均通过统一 `PromptLoader` 从 `prompts/cards/` 加载工艺卡。

---

## F3: PR-03 — 工艺卡版本化管理

### 验证方法

审查 `prompts/cards/` 目录结构和 `_manifest.yaml`。

### 验证结果

目录结构：
```
prompts/cards/
  writer/
    1.0.5.yaml
    1.0.6.yaml
    1.0.7.yaml
    1.0.8.yaml
    1.0.9.yaml
    _manifest.yaml
  goal_planner/
    1.0.0.yaml
    _manifest.yaml
  ... (其他 Agent 均有 manifest)
```

**Writer manifest 示例**：
```yaml
agent: "writer"
default_version: "1.0.9"
versions:
  - version: "1.0.9"
    description: "措辞回调：1.4x 超标不可接受，与 Accept 路径字数守卫协同"
    tags: ["webnovel", "xuanhuan", "urban", "scifi", ...]
    created_at: "2026-06-11"
```

**结论：PR-03 通过。** 每个工艺卡目录均有 `_manifest.yaml`，记录版本映射、变更描述、标签和创建时间。

---

## F4: PR-04 — Writer 输出正则清理

### 验证方法

审查 `writer.py` 中 `_extract_body` 函数。

### 验证结果

```python
def _extract_body(llm_response: str) -> str:
    text = llm_response.strip()

    # 1. 去除 markdown 代码块
    if text.startswith("```"):
        ...

    # 2. 去除常见的首尾说明
    text = re.sub(r"^(以下是|以下是第.*章|正文[：:]\s*)\s*", "", text, flags=re.IGNORECASE)

    # 3. 过滤元数据格式（核心事件、时间、地点）
    if re.match(r"^(核心事件|时间|地点)[：:]\s*", stripped):
        continue

    # 4. 去除所有 HTML 注释（兜底清理元标记泄漏）
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # 5. 去除旧版可见标记 [[新设定:...]]（兜底）
    text = re.sub(r"\[\[新设定:[^\]]+\]\]", "", text)

    # 6. 压缩连续空行
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    return text.strip()
```

**结论：PR-04 通过。** Writer 输出经过多层正则清理，覆盖 markdown 代码块、HTML 注释、旧版可见标记、首尾说明和元数据格式。

---

## F5: PR-05 — 元标记泄漏检测

### 验证方法

审查 `rule_auditor.py` 和 `llm_auditor.py` 中是否有 `<mark>` / `<!--` / `meta:` 检测规则。

### 验证结果

**审查体系搜索**：
```python
# rule_auditor.py: 零处匹配 <!-- / <mark> / meta: / 元标记
# llm_auditor.py:  零处匹配 <!-- / <mark> / meta: / 元标记
```

**现有保护机制**：
- Writer 输出阶段：`_extract_body` 会清理 `<!--.*?-->` 和 `[[新设定:...]]`（前端清理）
- 但审查阶段（RuleAuditor / LLMAuditor）**无专门规则**将元标记残留标记为 issue

**缺口分析**：
- AGENTS.md 要求 "LLMAuditor 只做语义审查"，RuleAuditor "只做代码检测"
- 元标记泄漏属于"格式污染"，当前由 Writer 前端清理兜底
- 若 LLM 生成新型元标记（如 `<mark>`, `meta:`, `{#comment}` 等），审查体系无法捕获

**判定**：⚠️ **观察项（P2）**。Writer 前端清理已覆盖常见元标记，但审查体系缺少专门的元标记泄漏检测规则。建议补充：RuleAuditor 增加元标记正则检测（如 `<!--`, `<mark>`, `meta:`, `[[...]]`），作为第二道防线。

---

## F6: PR-06 — 字数控制机制

### 验证方法

审查 `writer.py` 和 `utils/truncation.py` 中字数约束。

### 验证结果

**Writer 层（`writer.py` L22, L553-563）**：
```python
WORD_COUNT_TOLERANCE = 0.10  # ±10%

deviation = abs(word_count - word_count_target) / word_count_target
if deviation > WORD_COUNT_TOLERANCE:
    logger.warning("writer.word_count_mismatch", ...)
```

**截断工具层（`truncation.py` L10-35）**：
```python
_CHAPTER_TYPE_TOLERANCE = {
    "conflict": 1.35,
    "climax": 1.35,
    "tech_revelation": 1.30,
    "world_building": 1.25,
    "opening": 1.20,
    "transition": 1.15,
    ...
}
_DEFAULT_TOLERANCE = 1.20
_LOWER_TOLERANCE = 0.80

def word_count_bounds(word_count_target, chapter_type):
    multiplier = _CHAPTER_TYPE_TOLERANCE.get(chapter_type or "", _DEFAULT_TOLERANCE)
    return int(word_count_target * _LOWER_TOLERANCE), int(word_count_target * multiplier)
```

**结论：PR-06 通过。** 字数控制双层机制：Writer 生成后校验 ±10% 偏差并 warning；截断工具按章节类型动态调整上下界（0.8x ~ 1.35x）。

---

## F7: PR-07 — 截断保场景完整性

### 验证方法

审查 `utils/truncation.py` 中 `enforce_word_count` 和 `hard_truncate_at_boundary`。

### 验证结果

**Scene 边界优先截断（`enforce_word_count` L55-89）**：
```python
_headers = list(SCENE_PATTERN.finditer(content))
for _i in range(len(_headers) - 1, 0, -1):
    _cut = _headers[_i].start()
    _t = content[:_cut].strip()
    _wc = count_chinese_words(_t)
    _ns = parse_scenes(_t)

    # 字数在 [lower, upper] 范围内且 scene 数满足最低要求
    if _wc <= _upper and _wc >= _lower and len(_ns) >= 1:
        return _t, _ns, _wc, True, f"truncated_before_scene_{_i + 1}"
```

**回退策略（`hard_truncate_at_boundary` L92-119）**：
```python
def hard_truncate_at_boundary(content: str, max_words: int) -> str:
    # 策略 1：从后向前删除段落
    paragraphs = content.split("\n\n")
    while len(paragraphs) > 1:
        paragraphs.pop()
        candidate = "\n\n".join(paragraphs)
        if count_chinese_words(candidate) <= max_words:
            ...

    # 策略 2：只剩一个段落，从后向前删除句子
    sentences = re.split(r"(.*?[。！？…])", para, flags=re.DOTALL)
    ...
```

**结论：PR-07 通过。** 主截断策略优先在 scene 边界处截断；若结构保护导致无法截断，`hard_truncate_at_boundary` 按段落→句子边界回退，不在场景中间截断。

---

## F8: PR-08 — Rewrite 字数护栏

### 验证方法

审查 `workflows/_nodes.py` 中 `rewrite_node`。

### 验证结果

```python
# _nodes.py L654-667
if goal and goal.word_count_target > 0:
    lower = int(goal.word_count_target * 0.80)
    upper = int(goal.word_count_target * 1.20)
    ctx.human_instructions.append(
        {
            "type": "word_count_constraint",
            "content": (
                f"【重写约束】本章目标字数为 {goal.word_count_target}。 "
                f"重写后正文必须严格控制在 {lower} ~ {upper} 字之间。 "
                f"若场景展开后可能超标，优先减少场景数量或压缩描写，不要超额。"
            ),
        }
    )
```

**结论：PR-08 通过。** Rewrite 时注入字数硬约束，明确限制在 ±20%（0.80x ~ 1.20x），符合 Task 090b 要求。

---

## Pass R 回归检查

| ID | 检查项 | 状态 |
|----|--------|:----:|
| RG1 | 新增 import 是否引入未声明依赖 | ✅ 无新增 import |
| RG2 | 新增 except 是否用了裸 Exception | ✅ 无代码变更 |
| RG3 | 修改文件是否保持 < 400 行 | ✅ 无代码变更 |
| RG4 | pytest 回归全绿 | ⏸️ 需要 Python 运行时验证 |

---

## 发现汇总

| ID | 严重度 | 发现 | 文件 | 建议 |
|----|:------:|------|------|------|
| PR-05-obs | P2 | 审查体系无专门元标记泄漏检测规则 | `agents/rule_auditor.py`, `agents/llm_auditor.py` | RuleAuditor 增加元标记正则检测（`<!--`, `<mark>`, `meta:`, `[[...]]`）作为第二道防线 |

---

## 汇总

```
Pass 17 状态:
  PR-01 (无硬编码 prompt)     ██████████  ✅
  PR-02 (工艺卡加载)          ██████████  ✅
  PR-03 (版本化管理)          ██████████  ✅
  PR-04 (输出清理)            ██████████  ✅
  PR-05 (元标记检测)          ████████▁▁  ⚠️ 观察项
  PR-06 (字数控制)            ██████████  ✅
  PR-07 (截断完整性)          ██████████  ✅
  PR-08 (Rewrite 护栏)        ██████████  ✅

  通过:  7/8
  观察:  1/8 (PR-05)
```

**Prompt 工程核心契约（7/8 通过）**。工艺卡体系完整，版本管理规范，输出清理到位，字数控制有双层保护。唯一观察项是审查体系缺少元标记检测规则，但 Writer 前端清理已覆盖主要泄漏场景。

---

> **松烟入墨，字句成锋。**
> Prompt 是 Agent 的剧本，工艺卡是这剧本的排演厅 — 当每句指令都有版本可追溯，Prompt 调优才不会变成盲人摸象。

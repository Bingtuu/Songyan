# Task 160: 元标记泄漏根治（正则补全 + Writer 强制清洗 + RuleAuditor 阻塞）

> **Phase**: V7 阶段 W（篇章级质量修复）
> **优先级**: P0（52/150 章可读性硬伤，读者一眼可见；P 项 T9「零元标记泄漏」的直接前置）
> **依赖**: 无上游代码依赖；与 161（去重）、162（时间线）同域可并行，但均独立
> **预计工作量**: 小（正则 + 清洗默认值 + severity 升级 + 单测；不改生成/门禁架构）
> **事实入口**: `tasks/V7-README.md`；规划：`docs/v7-plan.md` §3 阶段 W

---

## Goal

根治 `run-bba292da` 中 **52/150 章正文泄漏 `### Scene N` / `Scene N:` 等元标记** 的可读性硬伤：补全检测正则覆盖裸标记与无数字变体、让 Writer 输出**默认强制清洗**场景标记、把 RuleAuditor 的元标记泄漏从"观测（info）"升级为 **accept 前阻塞项**——三道防线叠加，使元标记不再进入 accepted 正文。

## Context

设计核实（2026-07-04，创建前对主干代码核对）：

- **检测正则有缺口**：`_MARKDOWN_SCENE_PATTERNS`（`src/songyan/agents/rule_auditor.py:68-71`）只有两条：
  - `(?im)^\s*###\s*Scene\s+\d+.*`（要求 `Scene` 后跟**数字**）
  - `(?im)^\s*Scene\s+\d+[:：].*`（裸标题，同样要求数字）
  → 字面 `### Scene N`（占位符 N 未被 LLM 替换成数字）、`## Scene 1`（少一个 `#`）、`**Scene 1**` 等变体会**漏检**。这是 52 章泄漏的检测侧根因。
- **检测结果仅 info、不阻塞**：`detect_markdown_scene_titles`（`rule_auditor.py:98-119`）把每个匹配的 `severity` 硬编码为 `"info"`；`rule_auditor.py:476-478` 只在 `markdown_scene_title_count > 0` 时追加一条**建议**性 message，不影响 accept 判定。
- **Writer 清洗默认关闭**：`_extract_body(llm_response, strip_scene_markers=False)`（`src/songyan/agents/writer.py:408`）**默认不清洗**显式场景编号。真正删除 `### Scene N`（带数字）的分支只在 `strip_scene_markers=True` 时走（`writer.py:439-446`）；默认路径仅删除 `### Scene 后非数字`（`writer.py:437`）与部分元数据行，覆盖不全。需核实 `run_chapter_pipeline` 调用 `_extract_body` 时是否传 `strip_scene_markers`——若默认 False 则 52 章泄漏的生成侧根因即在此。
- **已有基础设施可复用**：`MetaTagLeakMatch` 模型（`models/review.py`）、`markdown_scene_title_matches` / `markdown_scene_title_count` 字段（`review.py:160-161`）、`detect_meta_tag_leaks`（HTML 注释/mark/meta 前缀，severity 已是 `major`，`rule_auditor.py:74-95`）——本 Task 是**补全 + 升级**，不新建体系。

**边界**：这是"检测覆盖 + 清洗默认 + severity 升级"的确定性工程修复，**不引入 LLM 判断**，不改 Writer 生成 prompt 主体（清洗是后处理）。scene_parser（`utils/scene_parser.py`）按 `### Scene N` 分场景的能力**保留**——它是内部解析用途，与"正文泄漏"是两回事；清洗只作用于**最终入库正文**，不破坏中间分场景逻辑。

## In Scope（必须完成）

- [ ] **补全检测正则**：`_MARKDOWN_SCENE_PATTERNS` 增加覆盖——字面 `### Scene N`（`N` 为占位符非数字）、`##`/`#` 少井号变体、`**Scene N**` 加粗变体、中文"场景 N/场景一"等。以 `run-bba292da` 的 52 章真实泄漏样本为准，确保新正则**全覆盖**已知泄漏形态。
- [ ] **Writer 输出默认强制清洗**：`_extract_body` 的 `strip_scene_markers` **默认改为 True**（或在 `run_chapter_pipeline` 调用处显式传 True），使显式场景编号不进入入库正文；确认清洗后仍保留空行分场景结构（不破坏正文段落）。
- [ ] **RuleAuditor severity 升级为阻塞**：`detect_markdown_scene_titles` 匹配项 severity 从 `info` 升为 **accept 前阻塞级**（对齐 `detect_meta_tag_leaks` 的 `major`）；在 accept 判定链路中，`markdown_scene_title_count > 0` 触发**修订/不通过**而非仅建议。阻塞口径须与现有 gate 语义一致（走 RuleAuditor → 修订路径，不新增门禁类型）。
- [ ] **回归钉死**：单测覆盖 52 章泄漏样本的**代表形态子集**，验证修复后检测命中 + 清洗清零；验证正常正文（空行分场景、无元标记）不误伤。

## Out of Scope（明确不做）

- 不做段落去重（Task 161）、时间线检测（Task 162）、概念预算（Task 163）。
- 不改 scene_parser 的内部分场景逻辑（它用 `### Scene N` 是解析用途，非泄漏）。
- 不引入 LLM 判断元标记；保持纯正则 + 后处理清洗的确定性修复。
- 不做洁净度度量入库（Task 164 统一做，本 Task 只保证"不泄漏 + 会阻塞"）。

## 接口契约

```python
# rule_auditor.py：正则表增补（新增变体，不删旧）
_MARKDOWN_SCENE_PATTERNS: list[tuple[str, str]] = [
    (r"(?im)^\s*#{1,3}\s*Scene\s+(\d+|N).*", "Markdown场景标题"),
    (r"(?im)^\s*Scene\s+(\d+|N)\s*[:：].*", "裸场景标题"),
    (r"(?im)^\s*\*\*Scene\s+(\d+|N)\*\*.*", "加粗场景标题"),
    # ... 以 52 章实测形态为准补全
]

# writer.py：清洗默认开启
def _extract_body(llm_response: str, strip_scene_markers: bool = True) -> str:
    """默认清洗显式场景编号，使其不进入入库正文."""

# detect_markdown_scene_titles：severity 升级
#   severity="major"（accept 前阻塞），message 保持定位信息
```

## 测试要求

### Layer 2: 模块测试（`tests/test_160_meta_tag_eradication.py`）
- [ ] **52 章泄漏形态回归**：构造 `### Scene N` / `## Scene 1` / `**Scene 2**` / `Scene 3:` / 中文变体等代表样本，断言 `detect_markdown_scene_titles` **全部命中**且 severity=major。
- [ ] **清洗验证**：喂含上述标记的 LLM 响应给 `_extract_body`（默认参数），断言输出**零元标记**且正文段落完整（空行分场景保留）。
- [ ] **阻塞验证**：`markdown_scene_title_count > 0` 时 accept 判定走修订/不通过分支（Mock 审计链路），不再仅追加建议。
- [ ] **不误伤**：正常正文（无标记、空行分场景）检测命中数=0、清洗后与输入等价。

### Layer 3: 真实样本复算（可选，归因佐证）
- [ ] 取 `run-bba292da` 中若干泄漏章的入库正文，复算新检测命中数；确认修复前后差异符合 52 章预期。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_160_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归（尤其 scene_parser / writer / rule_auditor 既有单测）。
- [ ] 新正则覆盖 `run-bba292da` 52 章已知泄漏形态；`_extract_body` 默认清洗；`detect_markdown_scene_titles` severity=major 且进入 accept 阻塞链路。
- [ ] 正常正文不误伤（检测=0、清洗幂等）。
- [ ] 不违反不可违背规则：纯代码检测 + 后处理清洗，无新增 LLM/Agent/门禁类型；RuleAuditor 仍只做代码检测。
- [ ] 生成 `tasks/160-meta-tag-leak-eradication-DONE.md`（含新正则清单、清洗默认值改动点、severity 升级点、52 章样本命中率）。
- [ ] 更新 `tasks/V7-README.md`（160 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v7-plan.md` §0（52 章元标记泄漏缺陷行）、§3 阶段 W（Task 160 行）、§4 T9
- 现有代码：`src/songyan/agents/rule_auditor.py:61-119`（`_META_TAG_PATTERNS` / `_MARKDOWN_SCENE_PATTERNS` / `detect_meta_tag_leaks` / `detect_markdown_scene_titles`）、`rule_auditor.py:476-478`（当前仅建议）、`src/songyan/agents/writer.py:408-490`（`_extract_body` / `strip_scene_markers`）、`src/songyan/utils/scene_parser.py`（内部分场景，勿破坏）
- 模型：`src/songyan/models/review.py:160-161`（`markdown_scene_title_*` 字段）、`MetaTagLeakMatch`
- 缺陷证据：`docs/reports/task-159-v6-final-acceptance-report.md` + `run-bba292da` 正文质量评估

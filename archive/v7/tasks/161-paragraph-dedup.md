# Task 161: 段落级去重（整段复制根治 + 重复长段落检测）

> **Phase**: V7 阶段 W（篇章级质量修复）
> **优先级**: P0（19/150 章连贯性硬伤，Ch75 最重；P 项 T9「零整段落重复」的直接前置）
> **依赖**: 无上游代码依赖；与 160（元标记）、162（时间线）同域可并行
> **预计工作量**: 中（拼接侧去重 + 检测器 + 单测；需谨慎不误删合法重复短句）
> **事实入口**: `tasks/V7-README.md`；规划：`docs/v7-plan.md` §3 阶段 W

---

## Goal

根治 `run-bba292da` 中 **19/150 章（Ch75 最重）出现整段落逐字重复** 的连贯性硬伤：在**修订/合并拼接环节增加段落级去重**（消除同一长段落被重复拼入），并新增 RuleAuditor **"同章重复长段落"检测**（含定位）作为回归防线——两者叠加使重复段落不再进入 accepted 正文。

## Context

设计核实（2026-07-04，创建前对主干代码核对）：

- **拼接侧根因**：分段修订 `run_segmented_revision`（`src/songyan/agents/revision_handler/_segmented_revision.py:258-`）对每个 scene 段分别修订后，用 `_reassemble_content(scenes, revised_scenes)`（`_segmented_revision.py:433-442`）以 `"\n\n".join(parts)` 重新拼接。若某段修订输出**重复携带了相邻段内容**（LLM 修订时把上下文一并重写返回），或回退分支重复保留原段，拼接后即出现整段逐字重复。`_reassemble_content` 当前**无去重**。这是 Ch75 整段复制的最可能根因。
- **回退分支的重复风险**：`_segmented_revision.py:482-503` 的字数超限二次截断/硬截断分支会回退到 `original_content`；若与已拼接内容部分重叠，可能引入重复。
- **无检测防线**：RuleAuditor 现有 `detect_meta_tag_leaks` / `detect_markdown_scene_titles` / 节奏/疲劳词检测，但**无"同章内重复长段落"检测**。19 章重复因此既无拼接侧拦截、也无审计侧发现，直接 accept。
- **去重需谨慎**：合法文本可能有**短句重复**（如对话中的"不、不、不"、口号、章节回环呼应），去重**只针对长段落级别**（≥ 阈值字数、≥ 阈值相似度），不碰短句，避免误删合法修辞。

**边界**：这是"拼接去重 + 重复检测"的确定性工程修复，**不引入 LLM 判断**。去重发生在**入库前的拼接/后处理**，检测作为回归防线。不改分段修订的 LLM 修订逻辑本身（只在其输出拼接后去重）。

## In Scope（必须完成）

- [ ] **拼接侧段落去重**：在 `_reassemble_content`（或其下游、入库前）增加**段落级去重**——对拼接后的段落列表，检出**逐字相同或高相似（≥阈值，如 0.9）的长段落（≥阈值字数，如 100 字）**并去重（保留首次出现）。去重规则确定、可单测、可解释；短段落/短句不参与。
- [ ] **RuleAuditor 重复长段落检测**：新增 `detect_duplicate_paragraphs(text) -> list[...]`——检出同章内重复的长段落并给出**定位**（复用 `locate_position` / `split_paragraphs`）。检测结果入 `RuleAuditResult`（新增字段，参照 `markdown_scene_title_matches` 模式）。**先作为诊断/告警**（是否升级为 accept 阻塞由 164 洁净度度量统一定口径；本 Task 至少保证"能检出并定位"）。
- [ ] **阈值可配、有默认**：长段落字数阈值、相似度阈值以 `run-bba292da` 19 章样本（尤其 Ch75）标定一个合理默认，确保既能抓住整段复制、又不误伤合法短重复。
- [ ] **回归钉死**：单测覆盖 Ch75 式整段复制样本，验证去重后重复清零、检测能命中；验证含合法短句重复的正文不被误删/误报。

## Out of Scope（明确不做）

- 不做元标记清洗（Task 160）、时间线检测（Task 162）、概念预算（Task 163）。
- 不改分段修订的 LLM 修订调用逻辑（只在其输出拼接后去重）。
- 不做跨章重复检测（本 Task 只治**同章内**重复；跨章相似是另一类问题，不在 W 范围）。
- 不引入 LLM 语义去重——保持"长段落 + 高相似度"的确定性规则。
- 去重是否升级为 accept 硬阻塞留 Task 164 统一定（本 Task 保证拼接侧不再产生 + 审计侧能发现）。

## 接口契约

```python
# _segmented_revision.py：拼接后去重（或独立后处理函数，入库前调用）
def _dedup_long_paragraphs(
    paragraphs: list[str],
    *,
    min_chars: int = 100,
    similarity_threshold: float = 0.9,
) -> list[str]:
    """去除逐字相同/高相似的长段落，保留首次出现；短段落不参与."""

# rule_auditor.py：同章重复长段落检测（诊断 + 定位）
def detect_duplicate_paragraphs(
    text: str,
    *,
    min_chars: int = 100,
    similarity_threshold: float = 0.9,
) -> list[DuplicateParagraphMatch]:
    """检出同章内重复的长段落并定位（观测/告警）."""
```

## 测试要求

### Layer 2: 模块测试（`tests/test_161_paragraph_dedup.py`）
- [ ] **Ch75 式整段复制**：构造含逐字重复长段落的样本，断言 `_dedup_long_paragraphs` 去重后仅保留一份、正文其余内容不动。
- [ ] **高相似非逐字**：段落有细微差异但相似度 ≥ 阈值，验证按规则去重（或按选定策略保留，行为确定且单测钉死）。
- [ ] **合法短句重复不误删**：对话/口号/短回环重复（< min_chars），断言**不被去重**。
- [ ] **检测器命中 + 定位**：`detect_duplicate_paragraphs` 对重复样本命中并给出正确 location；对无重复正文命中数=0。
- [ ] **拼接集成**：Mock 分段修订输出含重复段，验证 `_reassemble_content` 下游去重后入库正文无重复。

### Layer 3: 真实样本复算（可选，归因佐证）
- [ ] 取 `run-bba292da` 中 Ch75 等重复章入库正文，复算检测命中数；确认去重逻辑能覆盖 19 章实测形态。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_161_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归（尤其 revision_handler 既有单测）。
- [ ] 拼接侧去重能消除 Ch75 式整段复制；`detect_duplicate_paragraphs` 能检出并定位 19 章重复形态；合法短句重复不误伤。
- [ ] 阈值有以真实样本标定的合理默认，且可配置、可单测。
- [ ] 不违反不可违背规则：RevisionHandler 仍只做 patch（不整章重写）；去重是后处理去重、非重写；纯代码检测无新增 LLM；版本不可覆盖（去重发生在生成新版本内容时，不改历史版本）。
- [ ] 生成 `archive/v7/tasks/161-paragraph-dedup-DONE.md`（含去重规则、阈值标定依据、检测器接口、Ch75/19 章样本命中率）。
- [ ] 更新 `tasks/V7-README.md`（161 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v7-plan.md` §0（19 章整段重复缺陷行）、§3 阶段 W（Task 161 行）、§4 T9
- 现有代码：`src/songyan/agents/revision_handler/_segmented_revision.py:258-442`（`run_segmented_revision` / `_reassemble_content` / 回退分支 482-513）、`src/songyan/agents/rule_auditor.py`（检测器风格 + `locate_position` / `split_paragraphs`）
- 模型：`src/songyan/models/review.py`（`RuleAuditResult` / `MetaTagLeakMatch` 字段模式，供新增 `DuplicateParagraphMatch` 参照）
- 缺陷证据：`archive/v6/reports/task-159-v6-final-acceptance-report.md` + `run-bba292da` 正文质量评估（Ch75 最重）

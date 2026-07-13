# Pass 17: Agent 边界与结算模块审计报告

> **审计日期**: 2026-07-13
> **项目基线**: V7 Task 171w 完成后
> **审查范围**: `src/songyan/agents/writer.py`, `revision_handler/*`, `rule_auditor.py`, `llm_auditor.py`, `literary_auditor.py`, `settlement_extractor/*`, `summary_writer.py`, `workflows/review_merger.py`

---

## 执行摘要

Agent 边界总体清晰：Writer、Auditor、LiteraryAuditor、ReviewMerger、SummaryWriter 均守界。**RevisionHandler 存在 1 个 P0 级越权问题**（对 patchable issue 做整章重写），以及 `source_quote` 空字符串会绕过校验的 P1 级合规缺口。其余发现为内联 Prompt、死代码、硬编码主角名等 P2 级债务。

| 级别 | 数量 | 关键问题 |
|---|---|---|
| P0 | 1 | RevisionHandler 对 patchable issue 做整章重写 |
| P1 | 3 | scene_split 整章重写、内联 Prompt、空 source_quote 绕过校验 |
| P2 | 5 | 裸 except、硬编码主角名、死代码、重复导入 |

---

## P0 级问题

### P0-1 RevisionHandler 对 patchable issue 做整章重写

- **文件路径**: `src/songyan/agents/revision_handler/__init__.py:590-636`
- **代码片段**:
  ```python
  prompt = (
      "你是小说编辑。以下章节缺少一些前文的 critical 设定回收。"
      "请在保持原有叙事、不删除已有内容的前提下，为每个设定在合适位置插入一处自然提及。\n\n"
      "要求：\n"
      ...
      "4. 输出完整修订后的正文，不要添加解释、总结或 markdown 代码块。\n\n"
      f"缺失设定：{names}\n\n"
      f"正文：\n{content}"
  )
  ```
- **问题描述**: `_patch_mandatory_reference_missing` 用于修复 `fix_type="patch"` 的 `rule-mr-*` issue，但直接向 LLM 索要“完整修订后的正文”。
- **潜在影响**: 违反“RevisionHandler 只做 patch，不整章重写”。整章重写会引入新 AI 腔、疲劳词、钩子丢失等副作用，且与 `filter_patchable_issues` 中仅保留 `fix_type == "patch"` 的意图冲突。
- **修复建议**: 改为局部 patch：先定位正文中适合插入设定的段落，生成只包含插入句的 `Patch`，通过 `_apply_patches` 应用；并像其它 patchable issue 一样走统一 patch 引擎。

---

## P1 级问题

### P1-1 RevisionHandler 对 `scene_split` issue 做整章结构重写

- **文件路径**: `src/songyan/agents/revision_handler/__init__.py:542-562`
- **问题描述**: `_handle_scene_split` 对 `fix_type="scene_split"` 的 issue 调用 LLM 输出“完整修订后的正文”，实质是整章重写。
- **潜在影响**: 容易引入字数失控、hook 丢失、新增 AI 腔等问题；且该路径没有复用 `_enforce_revision_word_count` 等后处理。
- **修复建议**: 用代码化的场景拆分（按字数/段落/空行）替代 LLM 重写；若必须 LLM，应限制为仅输出场景分隔位置，再由代码拼接，并在输出后补一次 rule audit + 字数/保留率守卫。

### P1-2 RevisionHandler / 分段修订内联 Prompt 未外置

- **文件位置**:
  - `src/songyan/agents/revision_handler/__init__.py:548-562`（`_handle_scene_split`）
  - `src/songyan/agents/revision_handler/__init__.py:571-587`（`_handle_scene_overflow`，已死代码）
  - `src/songyan/agents/revision_handler/__init__.py:608-617`（`_patch_mandatory_reference_missing`）
  - `src/songyan/agents/revision_handler/_segmented_revision.py:180-198`（`_render_scene_prompt`）
- **问题描述**: 上述函数直接在代码中拼装中文/英文 Prompt，未放入 `prompts/` 工艺卡系统。
- **潜在影响**: 违反“Prompt 放在 `prompts/`，代码中不写长 prompt”。内联 Prompt 难以版本化、A/B 测试和审计。
- **修复建议**: 在 `prompts/cards/` 中新增 `revision_handler_scene_split`、`revision_handler_mandatory_reference`、`revision_handler_segmented_scene` 等工艺卡，通过 `get_prompt_loader()` 渲染。

### P1-3 `source_quote` 过滤后会清空为空字符串，导致校验放行

- **文件路径**:
  - `src/songyan/agents/settlement_extractor/_quote_filter.py:32-41`
  - `src/songyan/agents/settlement_extractor/_quote_filter.py:125-136`, `:166-178`, `:180-201`
  - `src/songyan/agents/settlement_extractor/_validate.py:671-682`
- **代码片段**:
  ```python
  if not quote:
      return True  # 空 quote 不视为错误，直接跳过
  ```
  ```python
  if update.source_quote and not _quote_in_content(update.source_quote, content):
      errors.append(...)
  ```
- **问题描述**: `_is_valid_source_quote` 对空 quote 返回 `True`；`filter_settlement_source_quotes` 将无效 quote 清空为 `""`；`_validate_settlement` 仅校验非空 quote。
- **潜在影响**: 违反 AGENTS.md “`new_setting.source_quote` 必须在正文中存在”。LLM 生成的错误/幻觉 quote 被清空后即可通过校验，导致无证据的状态变更进入 settlement。
- **修复建议**:
  - 对 `NewSetting` 和 `CharacterUpdate` 要求 `source_quote` 非空且命中正文；空 quote 应记为校验错误。
  - 或在 `_quote_filter` 中将无法修复的条目标记为 `needs_human_review`，而不是简单清空。

---

## P2 级问题

### P2-1 LLMAuditor 使用过于宽泛的异常捕获

- **文件**: `src/songyan/agents/llm_auditor.py:244`
- **代码**:
  ```python
  try:
      data = parse_llm_response(llm_response)
      result = _build_llm_audit_result(data)
  except Exception:
      logger.error(...)
      raise
  ```
- **问题**: `except Exception` 会捕获所有异常，日志中无法区分异常类型。
- **修复建议**: 收窄为 `except (LLMResponseParseError, ValueError, KeyError, TypeError)`。

### P2-2 `rule_auditor.py` 残留硬编码主角名的静态 exposition 模式

- **文件**: `src/songyan/agents/rule_auditor.py:589-605`
- **代码**:
  ```python
  (
      "vision_dump",
      r"(?:他|她|林渊|宋晚|苏晚)看见了[^。，]{0,10}(?:建造者|他们|完整的画面|完整画面|一幕|一切|真相|过去|未来|自己)",
      "幻象/画面直接播放",
  ),
  ```
- **问题**: 写死 `林渊|宋晚|苏晚`，与 Task 171a “体裁解耦”注释不一致。
- **修复建议**: 删除该条目或替换为不含主角名的通配占位符。

### P2-3 死代码 `_handle_scene_overflow` 及内联 Prompt

- **文件**: `src/songyan/agents/revision_handler/__init__.py:569-587`
- **问题**: 该函数定义了整章合并场景的 LLM Prompt，但在 `run_revision` 及任何其它函数中均未被调用。
- **修复建议**: 删除该函数。

### P2-4 `writer.py` 重复导入 `json`

- **文件**: `src/songyan/agents/writer.py:1-21`, `:205`
- **代码**:
  ```python
  import json as _json
  ```
- **修复建议**: 移除内部导入，统一使用顶部 `json`。

### P2-5 `summary_writer.py` 未校验输入来源

- **文件**: `src/songyan/agents/summary_writer.py`
- **问题**: 虽然 SummaryWriter 只基于 accepted 正文 + settlement，但未在入口处显式校验 `version.version_type == 'accepted'`。
- **修复建议**: 在 `_build_prompt` 或入口函数中增加断言/校验，确保只对 accepted 版本生成摘要。

---

## 正面发现

| 检查项 | 结论 |
|---|---|
| Writer 只做初稿 | ✅ `write_chapter` 仅生成 draft，不修订 |
| RevisionHandler 过滤 `rewrite_scene` | ✅ `filter_patchable_issues` 仅选 `fix_type == "patch"` |
| 自动修订最多 2 轮 | ✅ `phase1_graph.py` `_MAX_REVISION_ROUNDS=2` |
| LLMAuditor critical/major 必须带 evidence_quote | ✅ `_build_issue` 中无 evidence_quote 的 critical/major 被丢弃 |
| RuleAuditor 检测结果带定位 | ✅ `AiTellMatch`、`FatigueWordMatch`、`MetaTagLeakMatch` 等均含 `location` |
| LiteraryAuditor 不阻塞 accept | ✅ 仅返回 `literary_observation_id`，不参与 `_needs_revision` |
| ReviewMerger 不调用 LLM | ✅ `workflows/review_merger.py` 仅做内存合并 |
| SummaryWriter 基于 accepted 正文 + settlement | ✅ `_build_prompt` 使用 `content_preview` + `settlement_text` |
| Settlement old_value 回填 | ✅ `_validate_settlement` 用 DB 当前值回填 |
| Settlement numerical 公式校验 | ✅ `_numerical_formula_expected` + `NUMERICAL_TOLERANCE` |
| Settlement foreshadowing source_version_id | ✅ `_backfill_foreshadowing_source_version_ids` + 非空校验 |

---

## 验证结果

```powershell
# 相关测试
python -m pytest tests/ -q -k "revision or auditor or settlement or summary_writer" -x
# 658 passed, 1967 deselected, 1 xfailed

# ruff
ruff check src/ tests/
# All checks passed
```

---

## 修复优先级

1. **P0-1**: 将 `_patch_mandatory_reference_missing` 改为局部 patch，禁止整章重写。
2. **P1-1**: 评估 `_handle_scene_split` 是否需要整章 LLM 重写，或改为代码化拆分。
3. **P1-2**: 将 RevisionHandler 中的 4 处内联 Prompt 迁移到 `prompts/` 工艺卡。
4. **P1-3**: 收紧 `source_quote` 校验——空字符串不应通过 `NewSetting` / `CharacterUpdate` 的证据检查。
5. **P2**: 清理裸 except、硬编码主角名、死代码、重复导入。

# Pass 13: V7 后期新增子系统审计报告

> **审计日期**: 2026-07-13
> **项目基线**: V7 Task 171w 完成后，`run-e27b763f` Ch201-Ch220 20/20 accepted
> **全量测试**: `2623 passed, 2 skipped, 1 xfailed, 2 warnings in 423.32s`
> **审查范围**: Task 170-171w 新增或显著修改的子系统

---

## 执行摘要

本次审计聚焦 V7 阶段 Z 新增/硬化的文学护栏、文本洁净、creative brief 持久化等子系统。整体代码在功能测试层面稳定，静态检查通过，但发现 **3 个 P1 级问题**，主要集中在异常处理不完整、持久化审计选择逻辑脆弱和类型/死代码清理上。**未发现 P0 级问题**。

| 维度 | 结论 |
|---|---|
| 文本洁净 (T9 hard clean) | 检测项已扩展，测试覆盖到位，ruff 通过 |
| 文学护栏 (171v/171w) | 四字段持久化完成，正文 observe 已硬化，但 audit 选择逻辑有缺陷 |
| Creative Director | 对话风格卡生成异常捕获错误；brief builder 裸 except |
| 代码质量 | 存在死代码、重复项、类型标注不一致等 P2 债务 |

---

## 发现汇总

| 级别 | 数量 | 问题简述 |
|---|---|---|
| P0 | 0 | 无 |
| P1 | 3 | 异常捕获错误、裸 except、latest brief 选择逻辑脆弱 |
| P2 | 13 | 类型标注、死代码、重复计数、重复关键词、mypy 噪声、性能隐患 |

---

## P1 级问题

### P1-1 `generate_dialogue_style_cards` 捕获了错误的异常类型

- **文件路径**: `src/songyan/agents/creative_director/__init__.py:800-814`
- **代码片段**:
  ```python
  try:
      response_text = await call_llm(prompt, ...)
  except (RuntimeError, OSError, ConnectionError, ValueError, TypeError):
      ...
      return []

  try:
      data = _parse_llm_response(response_text)
  except (ValueError, TypeError, KeyError):
      ...
      return []
  ```
- **问题描述**: `call_llm` 实际抛出 `LLMError`，`_parse_llm_response` 实际抛出 `LLMResponseParseError`。这两个具体异常均不在捕获列表中，导致函数设计的“失败返回空列表”契约不成立，LLM/解析失败时会直接向上抛异常并中断 `workflows/_nodes.py:456` 的节点执行。
- **潜在影响**: 对话风格卡生成节点异常退出，不符合优雅降级设计。
- **修复建议**: 将捕获列表改为 `except (LLMError, LLMResponseParseError):`。

### P1-2 `_brief_builder.py` 使用裸 `except Exception`

- **文件路径**: `src/songyan/agents/creative_director/_brief_builder.py:196-207`, `:231-243`
- **代码片段**:
  ```python
  try:
      result.append(VoiceAnchor(...))
  except Exception:
      continue
  ```
- **问题描述**: 两处均使用裸 `Exception` 吞掉所有模型校验错误，违反 AGENTS.md“错误处理用自定义异常，不用裸 except”的规范。
- **潜在影响**: Pydantic `ValidationError`、类型错误乃至编程错误被静默吞掉，增加排查成本。
- **修复建议**: 捕获 `pydantic.ValidationError`（或 `ValueError`），并记录 `logger.warning` 说明丢弃原因。

### P1-3 `audit_171v_guardrail_persistence` 的“最新 brief”选择逻辑脆弱

- **文件路径**: `src/songyan/evals/literary_guardrails.py:98-109`
- **代码片段**:
  ```python
  SELECT chapter_number, MAX(created_at || brief_id) AS latest_key
  FROM creative_briefs
  ...
  GROUP BY chapter_number
  ```
- **问题描述**: 通过字符串拼接 `created_at || brief_id` 取最大值来决定“最新 brief”。`created_at` 默认精度为秒，同一秒内产生多条 brief 时，`brief_id`（UUID）的 lexicographic 大小与时间顺序无关，可能导致选中非时间最新的 brief。
- **潜在影响**: `brief_complete` / `accepted_replayable` 判断失真，影响 V7 后期质量度量可信度。
- **修复建议**: 使用 `ORDER BY created_at DESC, brief_id DESC LIMIT 1` 子查询，或引入自增 `rowid`/sequence 列来稳定取最新记录。

---

## P2 级问题

### P2-1 `detect_exposition_carriers` 中 `seen` 集合类型注解与实际 key 类型不一致

- **文件**: `src/songyan/agents/rule_auditor.py:793` 声明，`987, 1004, 1018, 1053, 1068, 1114` 等赋值处
- **问题**: `seen: set[tuple[int, int]]` 但多处写入 `tuple[str, int]`。
- **修复建议**: 将 `seen` 类型改为 `set[tuple[str | int, int]]`，或统一 key 格式。

### P2-2 `rule_auditor.py` 存在大量失效的 `type: ignore[arg-type]` 注释

- **文件**: `src/songyan/agents/rule_auditor.py:864, 887, 905, 927, 965, 992, 1009, 1023, 1094`
- **问题**: `ExpositionCarrierMatch.carrier_type` 已扩展为包含所有使用类型的 `Literal`，原 `type: ignore[arg-type]` 已失去意义，mypy 报 `unused-ignore`。
- **修复建议**: 删除这些注释。

### P2-3 `quoted_segment_re` 定义后未使用

- **文件**: `src/songyan/agents/rule_auditor.py:819`
- **问题**: `quoted_segment_re = re.compile(r'["“”]([^"“”]{20,800})["“”]')  # noqa: F841` 为死代码。
- **修复建议**: 删除该变量。

### P2-4 冲突打断关键词列表中存在重复项

- **文件**: `src/songyan/agents/rule_auditor.py:1044`
- **问题**: 全角问号 `"？"` 出现两次。
- **修复建议**: 去重。

### P2-5 `_check_mandatory_references` 的 `issues` 类型标注错误

- **文件**: `src/songyan/agents/rule_auditor.py:1447-1472`
- **问题**: `issues: list[str] = []` 实际追加 `dict`。
- **修复建议**: 改为 `issues: list[dict[str, Any]]`。

### P2-6 `collect_text_cleanliness_clean_issues` 中循环变量 `match` 类型复用导致 mypy 警告

- **文件**: `src/songyan/agents/rule_auditor.py:532-543`
- **问题**: 变量名复用导致 mypy 报错。
- **修复建议**: 第二个循环改用 `dup_match`。

### P2-7 `detect_exposition_carriers` 第 9/10 节可能重复计数

- **文件**: `src/songyan/agents/rule_auditor.py:1082-1137`
- **问题**: 第 3/9 节都基于 `direct_revelation_quote_re` 扫描；第 4/10 节都基于 `info_delivery_dialogue_re` 扫描。后两节未检查前面节是否已命中，同一段引语可能同时产生两个 `ExpositionCarrierMatch`。
- **潜在影响**: `exposition_carrier_count` 被重复计入。
- **修复建议**: 若 9/10 节是 3/4 节的“细化”，应在命中后跳过已统计 span；或说明去重规则。

### P2-8 `creative_director/__init__.py` 存在死代码

- **文件**: `src/songyan/agents/creative_director/__init__.py:58, 63-67`
- **问题**: `PROMPT_PATH` 与 `_load_prompt_template` 未被调用。
- **修复建议**: 删除死代码。

### P2-9 `_brief_builder.py` 类型标注不完整

- **文件**: `src/songyan/agents/creative_director/_brief_builder.py:83`, `:365`
- **问题**: `json.loads` 返回 `Any`；`_character_focus: list[dict] = []` 缺泛型参数。
- **修复建议**: 使用 `cast(dict[str, Any], json.loads(...))`；改为 `list[dict[str, Any]]`。

### P2-10 `literary_guardrail_observe.py` 与 `literary_guardrails.py` 的 `row_factory` lambda 导致 mypy 类型推断失败

- **文件**: `src/songyan/evals/literary_guardrail_observe.py:298, 341, 345`；`src/songyan/evals/literary_guardrails.py:94`
- **问题**: mypy 无法将 lambda 识别为有效的 `row_factory`。
- **修复建议**: 封装为具名函数并添加 `Callable[[sqlite3.Cursor, sqlite3.Row], dict[str, Any]]` 类型注解。

### P2-11 `collect_text_cleanliness_metrics` 全量加载 chapter_heads 后 Python 过滤

- **文件**: `src/songyan/evals/text_cleanliness.py:64-74`
- **问题**: 对长跑项目会一次性加载所有 heads，并在 Python 中过滤范围。
- **修复建议**: 在 `ChapterHeadRepository` 增加 `list_by_project_range(project_id, start, end)` 方法。

---

## 正面发现

- 新增文本洁净检测项（Markdown 标题、保护指令、斜杠拼接、纯省略号段、prompt/patch 指令、duplicate final sweep）已落地并通过测试。
- `creative_briefs` 四字段（protagonist_active_choice / new_concept_budget / fatigue_motif_replacements / supporting_character_goal）持久化完整，可回读审计。
- 正文 observe 已硬化；ReviewMerger 接线将缺失升级为 major patchable issue（CHARACTER_BEHAVIOR）。
- 未违反“Agent 不直连 DB”“版本不可覆盖”“state 只存 ID”等核心纪律。

---

## 验证结果

```powershell
# 目标测试集
python -m pytest tests/test_171w_text_guardrail_observe.py tests/test_171w_guardrail_persistence.py tests/test_171v_literary_guardrails.py tests/test_164_text_cleanliness.py tests/test_171t_text_cleanliness_final_sweep.py tests/test_rule_auditor.py tests/test_rule_auditor_dynamic_keywords.py tests/test_146_quality_debt.py -q
# 140 passed

# ruff
ruff check src/ tests/
# All checks passed
```

---

## 修复优先级

1. **P1-1**: 修正 `generate_dialogue_style_cards` 异常捕获类型。
2. **P1-2**: `_brief_builder.py` 裸 except 改为 `ValidationError` 并记录日志。
3. **P1-3**: `audit_171v_guardrail_persistence` 使用稳定排序取最新 brief。
4. **P2**: 类型标注、死代码、重复计数等代码卫生清理。

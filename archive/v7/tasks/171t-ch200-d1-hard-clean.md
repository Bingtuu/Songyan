# Task 171t: Ch200 D1 文本洁净量具补强

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 D1/D3 + Task 171 Ch200 复盘
> **类型**: D1 硬红线量具补强（T9 hard clean，不放宽门禁）
> **优先级**: P0（171u 清洁应用前置）
> **依赖**: 171p/171q/171r/171s；Ch200 run `run-fb39245c`；20% 抽读复盘
> **状态**: ✅ 完成（2026-07-12）

## 结论

Task 171 已取得 Ch200 规模化真实证据：`run-fb39245c` Ch1-Ch200 **200/200 accepted、gaps=[]、Halt=None**。但 20% 抽读复盘证明，当前 D1 hard clean 问题不只是 `duplicate=4` 和 stale report，T9 文本洁净量具本身还存在漏检。

新增发现的漏检类别：

| 类别 | 样例章节 | 说明 |
|---|---|---|
| Markdown 章标题泄漏 | Ch1、Ch2、Ch4、Ch47、Ch75 | accepted 正文出现 `# 第一章`、`# 第二章` 等 Markdown 标题 |
| 保护指令泄漏 | Ch84、Ch160 | accepted 正文出现 `【保护内容 — 请勿修改】` |
| 斜杠拼接痕迹 | Ch41、Ch76、Ch124、Ch164 | 出现非数值单位语境下的 `/` 拼接残留 |
| 纯省略号占位段 | Ch26、Ch32、Ch76、Ch101、Ch174 | 独立段落仅由省略号构成，疑似 patch 占位 |
| prompt/patch 指令泄漏 | Ch76 | 出现“每句末尾加重语气，机械眼闪烁红色警告”一类非叙事指令 |
| 近似/逐字重复 | Ch11、Ch84、Ch171 | frozen T9 已命中 `duplicate=4`，仍需 final sweep |

因此后续任务重新拆分：**171t 只补量具与 accept-time 检测能力**，不直接改 Ch200 DB；**171u 再基于补强后的量具清洁已接受正文与报告事实源**；**171v 才进入文学可读性护栏**。这样避免在量具尚有 false negative 时直接宣布 hard clean。

## 根因

1. **T9 meta 口径过窄**：当前 meta leak 更偏向传统元标记/LLM 标记，未覆盖 Markdown 标题、保护指令、prompt 指令残留等真实生成 artifact。
2. **T9 duplicate 已补 171q，但缺最后验收闸**：分段修订路径已对齐阈值，accepted head 仍可能来自其他路径或回滚路径，缺少 accept-time final sweep。
3. **斜杠与省略号没有语境判定**：数值单位、坐标、路径中的 `/` 是合法文本；拼接痕迹中的 `/` 需要独立规则。省略号作为句内标点合法，但纯省略号段落应判为 artifact。
4. **报告事实源必须先有可信检测**：如果量具仍漏检，后续 `--report` 即使重算也会给出虚假的 clean。

## 修复边界

### 做

1. 扩展 RuleAuditor / T9 文本洁净检测，新增 artifact 分类：
   - `markdown_heading_leak`
   - `protected_directive_leak`
   - `slash_splice_artifact`
   - `ellipsis_placeholder_paragraph`
   - `prompt_patch_instruction_leak`
2. 保留并加固 frozen duplicate 口径：
   - `detect_duplicate_paragraphs` 阈值不放宽；
   - Ch11 引号形态近重复继续命中；
   - Ch84/Ch171 逐字重复继续命中。
3. 设计 accept-time final sweep 的检测契约：
   - accept 前统一读取候选正文；
   - hard artifact 或 duplicate 未清零时不得静默 accept；
   - 可清理项进入 deterministic cleaner；
   - 不可确定项进入 isolate/human review。
4. 增加测试样本，覆盖本次 20% 抽读发现的全部类别。
5. 输出 171u 所需的清洁清单格式：chapter、version_id、issue_type、evidence_quote、suggested_action。

### 不做

- 不在 171t 中修改 Ch200 accepted/current head；
- 不覆盖旧 `chapter_versions`；
- 不降低 T9 阈值；
- 不把 duplicate 或 artifact 改成 report-only；
- 不做 LLM 整章重写；
- 不修复 stale continuity report 聚合（下放 171u）；
- 不改文学 Tier 2 口径（下放 171v）。

## 工程方案

### 1. Artifact 检测规则

新增检测应做到“严格命中真实 artifact，避免误伤叙事 UI”。

| issue_type | hard 判定 | 误伤保护 |
|---|---|---|
| `markdown_heading_leak` | 行首 `#` + 章节标题/数字标题 | 不匹配正文中的井号编号、技术符号 |
| `protected_directive_leak` | `保护内容`、`请勿修改`、`不要修改` | 无，均视为硬泄漏 |
| `slash_splice_artifact` | 中文句段之间孤立 `/`，两侧非数字单位/路径 | 放过 `m/s`、`km/s`、坐标、URL、文件路径 |
| `ellipsis_placeholder_paragraph` | 独立段落只含 `...`、`……` 或重复省略号 | 句内省略号合法 |
| `prompt_patch_instruction_leak` | “每句末尾加重语气”等写作指令进入正文 | 需 evidence_quote |

### 2. T9 Final Sweep 契约

171t 只定义并测试 sweep 判定，171u 再接入清洁应用。

```text
candidate content
  -> detect_text_cleanliness_artifacts
  -> detect_duplicate_paragraphs
  -> hard issue count == 0: allow accept
  -> hard issue count > 0:
       deterministic-cleanable: return clean plan
       uncertain: isolate / human review
```

### 3. 清洁清单输出

为 171u 提供稳定结构：

```text
CleanIssue:
  chapter_number
  version_id
  issue_type
  evidence_quote
  suggested_action
  deterministic_cleanable
```

## 测试

建议新增/扩展：

1. `tests/test_rule_auditor.py`
   - Markdown 标题泄漏；
   - 保护指令泄漏；
   - prompt/patch 指令泄漏；
   - 纯省略号段落；
   - 斜杠拼接 artifact 与合法单位/路径区分。
2. `tests/test_161_paragraph_dedup.py`
   - Ch11 引号形态近重复；
   - Ch84/Ch171 逐字重复；
   - 低于 40 字 refrain 保留。
3. 新增 `tests/test_171t_text_cleanliness_final_sweep.py`
   - 多 issue 聚合；
   - clean 文本不报 false positive；
   - hard issue 必须带 evidence_quote/定位。

## 验证命令

```powershell
python -m pytest tests/test_rule_auditor.py tests/test_161_paragraph_dedup.py tests/test_171t_text_cleanliness_final_sweep.py -q
ruff check src/songyan/agents/rule_auditor.py src/songyan/evals/db_metrics.py tests/
```

## 出口标准

| 项 | 标准 |
|---|---|
| artifact 检测 | 覆盖 Markdown 标题、保护指令、斜杠拼接、纯省略号段、prompt/patch 指令 |
| duplicate 检测 | Ch11/84/171 样本持续命中 |
| 误伤保护 | 合法单位/坐标/路径中的 `/` 不报 hard issue |
| evidence | 每个 hard issue 有定位与 `evidence_quote` |
| final sweep | 可输出 171u 清洁清单 |
| regressions | 目标 pytest + ruff 通过 |

## 实施结果（2026-07-12）

已完成 171t 开发：

1. `RuleAuditor` 新增 `detect_text_cleanliness_artifacts`，覆盖：
   - `markdown_heading_leak`
   - `protected_directive_leak`
   - `slash_splice_artifact`
   - `ellipsis_placeholder_paragraph`
   - `prompt_patch_instruction_leak`
2. `RuleAuditResult` 新增 `text_artifact_matches` / `text_artifact_count`，并保留现有 `meta_tag_matches`、`markdown_scene_title_matches`、`duplicate_paragraph_matches` 口径。
3. 新增 `TextCleanlinessCleanIssue` 与 `collect_text_cleanliness_clean_issues`，为 171u 输出稳定清洁清单：`chapter_number`、`version_id`、`issue_type`、`evidence_quote`、`evidence_location`、`suggested_action`、`deterministic_cleanable`。
4. `text_cleanliness` T9 metrics 已将新增 artifact 纳入 `meta_tag_leak_count` 硬红线；报告文案同步为“元标记/artifact”。
5. `ReviewMerger` 会将新增 artifact 转为 patchable major issue，进入自动修订/人工审查链路。
6. 误伤保护已覆盖：合法单位、坐标/比例、URL、文件路径中的 `/` 不报 `slash_splice_artifact`；句内省略号不报 `ellipsis_placeholder_paragraph`。

验证：

```powershell
python -m pytest tests/test_rule_auditor.py tests/test_161_paragraph_dedup.py tests/test_171t_text_cleanliness_final_sweep.py -q
# 104 passed

python -m pytest tests/test_171t_text_cleanliness_final_sweep.py tests/test_rule_auditor.py tests/test_160_meta_tag_eradication.py tests/test_161_paragraph_dedup.py tests/test_145_stage_a_metrics.py tests/test_171d_three_tier_contract.py -q
# 127 passed

ruff check src/ tests/
# All checks passed
```

## 与后续关系

171t 完成后进入 **171u：Ch200 D1 清洁应用与报告事实源复算**。只有 171u 用补强后的量具证明 Ch200 accepted 正文 T9 hard issue 全为 0，Task 171 才能从“规模跑通”升级为“D1 hard clean pass”。随后再进入 **171v：Ch200+ 文学性与可读性护栏**，最后启动 **Task 172：Ch250 过渡验证**。

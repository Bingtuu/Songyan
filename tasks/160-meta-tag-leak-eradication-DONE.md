# Task 160 DONE: 元标记泄漏根治

> **Phase**: V7 阶段 W（篇章级质量修复）
> **完成时间**: 2026-07-04
> **结论**: 完成。元标记泄漏从“观测提示”升级为“清洗 + 检测 + ReviewIssue 阻塞”三道防线。

---

## 目标回放

Task 160 针对 V6 `run-bba292da` 暴露的 52/150 章 `### Scene N` / `Scene N:` 等正文元标记泄漏，要求：

- 补全 RuleAuditor 场景标题检测正则；
- Writer / RevisionHandler 输出默认清洗显式场景编号；
- RuleAuditor 检测结果进入 accept 前修订/阻塞链路；
- 用单测钉死代表泄漏形态不复现。

## 已完成改动

| 模块 | 改动 |
|------|------|
| `src/songyan/agents/rule_auditor.py` | 扩展 `_MARKDOWN_SCENE_PATTERNS`，覆盖 `#`/`##`/`### Scene N`、裸 `Scene N:`、加粗 `**Scene N**`、中文 `场景一` 等变体；`detect_markdown_scene_titles` severity 从 `info` 升为 `major`。 |
| `src/songyan/agents/writer.py` | `_extract_body(..., strip_scene_markers=True)` 改为默认清洗；新增 `_strip_scene_marker_lines`；Writer 主路径最终入库正文强制清洗场景标题，同时保留一份内部 `parse_content` 给 scene parser 恢复显式场景边界。RevisionHandler 复用 `_extract_body()` 的路径随默认值一起清洗。 |
| `src/songyan/workflows/review_merger.py` | `meta_tag_matches` / `markdown_scene_title_matches` 转为 patchable major `ReviewIssue`；`rule-meta-*` / `rule-scene-*` 与 `rule-mr-*` 一样不计入普通规则 issue cap，避免被 `max_rule_issues=5` 截断。 |
| `tests/test_160_meta_tag_eradication.py` | 新增 Task 160 专项测试，覆盖代表形态检测、默认清洗、显式保留内部解析、ReviewMerger 阻塞接入、cap 保护。 |
| 既有测试 | 更新 `test_rule_auditor.py` 的 severity 断言；更新 `test_writer.py` 对默认清洗与字数统计的预期。 |

## 验收点

- **检测覆盖**：`### Scene N`、`## Scene 1 控制室`、`# Scene 2:`、`**Scene 3**`、`Scene 4:`、`### 场景一：`、`场景二：` 均命中 `detect_markdown_scene_titles`，且 severity=major。
- **清洗覆盖**：`_extract_body()` 默认删除显式场景编号；`strip_scene_markers=False` 仍可供内部解析保留数字型 `### Scene N`。
- **阻塞链路**：`review_merger._convert_rule_to_issues` 会生成 `rule-meta-*` / `rule-scene-*` patchable major issue；`merge_reviews` 后 `MergedReviewReport.has_major=True`，可进入修订/不通过路径。
- **cap 保护**：元标记 issue 不被普通规则 issue 上限截断。
- **不误伤**：普通句子如“场景一片混乱”不被识别为标题。

## 验证

```powershell
python -m pytest tests/test_160_meta_tag_eradication.py tests/test_rule_auditor.py tests/test_review_merger.py tests/test_writer.py -q
```

结果：`118 passed`

```powershell
python -m pytest tests/ -q
```

结果：`2278 passed, 2 skipped, 1 xfailed, 2 warnings`

```powershell
ruff check src/ tests/
```

结果：`All checks passed!`

## 边界

- 本 Task 不做段落去重、时间线一致性、概念预算，也不做洁净度入库；这些继续由 Task 161-164 承接。
- scene parser 仍保留按 `### Scene N` 解析内部场景的能力；清洗只保证最终入库正文不带显式场景标题。
- 未执行真实 `run-bba292da` 52 章全文复算；该项可在 Task 164/165 的洁净度入库与 Ch150 复跑中统一核验。

## 下一步

进入 Task 161：段落级去重（整段复制根治 + 重复长段落检测）。

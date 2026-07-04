# Task 161 DONE: 段落级去重

> **Phase**: V7 阶段 W（篇章级质量修复）
> **完成时间**: 2026-07-04
> **结论**: 完成。修订拼接侧已加入长段落去重，RuleAuditor 已新增重复长段落诊断信号。

---

## 目标回放

Task 161 针对 V6 `run-bba292da` 暴露的 19/150 章整段落逐字重复问题，要求：

- 在分段修订 / 合并拼接环节增加段落级去重；
- 新增 RuleAuditor 同章重复长段落检测；
- 只处理长段落，避免误删合法短句、口号、回环呼应；
- 用单测钉死 Ch75 式整段复制不复现。

## 已完成改动

| 模块 | 改动 |
|------|------|
| `src/songyan/agents/revision_handler/_segmented_revision.py` | 新增 `_dedup_long_paragraphs` / `_dedup_reassembled_content`，在 `_reassemble_content` 拼接后执行长段落去重。默认阈值：`min_chars=100`、`similarity_threshold=0.9`；短段落不参与，重复长段落保留首次出现。 |
| `src/songyan/models/review.py` | 新增 `DuplicateParagraphMatch`；`RuleAuditResult` 增加 `duplicate_paragraph_matches` / `duplicate_paragraph_count`。 |
| `src/songyan/models/__init__.py` | 导出 `DuplicateParagraphMatch`。 |
| `src/songyan/agents/rule_auditor.py` | 新增 `detect_duplicate_paragraphs`，基于段落定位 + `SequenceMatcher` 检出同章重复长段落；结果作为诊断字段进入 `RuleAuditResult`，不直接阻塞 accept。 |
| `tests/test_161_paragraph_dedup.py` | 新增 Task 161 专项测试，覆盖精确重复、高相似重复、短句重复不误删、检测定位、`run_rule_audit` 字段入账、`_reassemble_content` 集成。 |

## 去重规则

- **参与对象**：归一化后长度 `>= 100` 字符的段落。
- **重复判定**：空白归一化后完全相同，或 `SequenceMatcher` 相似度 `>= 0.9`。
- **保留策略**：保留首次出现的长段落，后续重复/高相似长段落删除。
- **误删控制**：短句、短对话、口号、回环呼应默认不参与去重。
- **阻塞边界**：本 Task 只提供拼接侧治理 + RuleAuditor 诊断；是否作为 T9 硬红线由 Task 164/165 统一冻结。

## 验收点

- Ch75 式整段复制样本在 `_reassemble_content` 后只保留一份。
- 高相似长段落（轻微改词）按阈值去重。
- 合法短重复不被删除、不被诊断为重复长段落。
- RuleAuditor 能给出重复段落的段落序号、原始段落序号、位置与相似度。

## 验证

```powershell
python -m pytest tests/test_161_paragraph_dedup.py tests/test_079_segmented_revision.py tests/test_rule_auditor.py -q
```

结果：`72 passed`

```powershell
python -m pytest tests/ -q
```

结果：`2287 passed, 2 skipped, 1 xfailed, 2 warnings`

```powershell
ruff check src/ tests/
```

结果：`All checks passed!`

## 边界

- 未执行 `run-bba292da` 19 章真实样本复算；真实样本覆盖率留 Task 164/165 的洁净度入库与 Ch150 复跑统一核验。
- 不做跨章重复检测。
- 不引入 LLM 语义去重，也不改分段修订 LLM 调用逻辑。
- 不把重复长段落直接转成 `ReviewIssue`，保持 Task 161 的诊断边界。

## 下一步

进入 Task 162：跨章时间线一致性检测（倒计时/时间戳矛盾，先诊断）。

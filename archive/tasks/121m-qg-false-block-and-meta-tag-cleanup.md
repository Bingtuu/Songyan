# Task 121m: QG False 硬拦截与元标记泄漏清理

> **日期**: 2026-06-22
> **类型**: V5.1 preflight / 工程阻断
> **状态**: ✅ 已完成（2026-06-22）
> **验证**: `pytest tests/ -q` 1729 passed, `ruff check src/ tests/` 通过
> **前置**: Task 121l `run-08689f68` 暴露 QG false 版本仍进入 settlement，且 Ch12 出现 `<!-- 新设定:... -->` 元标记泄漏。

---

## 1. 任务边界

本任务目标是用最小工程改动阻断两类劣质数据进入下游上下文池：

1. **QG false 放行**：`quality_gate_passed=False` 的章节不应执行 settlement 提取、状态写入、RAG 索引和生命周期清理。
2. **元标记泄漏**：writer 在正文中输出 `<!-- 新设定:... -->` HTML 注释，破坏叙事纯净度。

本任务聚焦：

- `settlement_extractor_node` 入口增加 QG false 硬拦截。
- `writer.py` 后处理清理所有 HTML 注释。
- `writer/1.0.9.yaml` prompt 删除或替换新设定标记指令。
- 单测覆盖新契约。

不做：

- 不修改 quality_gate 本身的评分逻辑。
- 不修改 settlement_extractor 的提取算法。
- 不调整上下文预算或 human_marks 生命周期（归 Task 121n）。
- 不做大范围 Prompt 文风调优（归 Task 121k）。

---

## 2. 事实入口

| 项 | 值 |
|----|----|
| 上一轮任务 | `tasks/121l-context-emergency-autohalt-review.md` |
| 发现问题 | `run-08689f68` Ch10 `quality_gate_passed=False` 仍完成 settlement；Ch12 正文出现 `<!-- 新设定:物理密钥|物品|林霜 -->` |
| 相关代码 | `src/songyan/workflows/_nodes.py` (settlement_extractor_node, human_gate_node) |
| 相关代码 | `src/songyan/agents/writer.py` (后处理函数) |
| 相关代码 | `prompts/cards/writer/1.0.9.yaml` (new_setting_mark section) |
| 单测 | `tests/test_phase2_graph.py`、`tests/test_108_core_nodes.py` |

---

## 3. 问题复盘

### 3.1 QG False 放行链

Ch10 日志：

```text
human_gate.decision chapter_number=10 convergence_failed=True decision=accept quality_gate_passed=False settlement_needs_human_review=False skip_settlement=False
settlement_extractor_node.contract_snapshot chapter_number=10 quality_gate_passed=False settlement_needs_human_review=False skip_settlement=False
settlement_extractor_node.settlement_applied chapter_number=10 character_updates=6 foreshadowing_updates=5 new_settings=8
```

 settlement 执行了 6 个角色更新、5 个伏笔更新、8 个新设定。这些劣质设定进入上下文池后，直接导致后续章节的 `soft_references` 和 `foreshadowing` 膨胀，加剧了 ContextEmergency。

### 3.2 元标记泄漏链

`writer/1.0.9.yaml` L355-368 明确指令：

```yaml
- **正确格式**：`<!-- 新设定:设定名|类型|关联角色 -->`
- **重要**：`<!-- ... -->` 是 HTML 注释格式，Markdown 渲染时会自动隐藏，读者阅读时看不到。
```

`writer.py` L459 的后处理故意保留了 HTML 注释，仅清理 `[[新设定:...]]`：

```python
# 去除可见的旧版设定标记 [[新设定:...]]（HTML 注释 <!-- 新设定:... --> 保留，对读者不可见）
text = re.sub(r"\[\[新设定:[^\]]+\]\]", "", text)
```

结果 Ch12 正文中出现：`<!-- 新设定:物理密钥|物品|林霜 -->`，直接污染正文。

---

## 4. 执行步骤

### Step A: QG False 硬拦截（`_nodes.py`）

在 `settlement_extractor_node`（约 L2044）`_skip_settlement` 分支之后、`extract_settlement` 调用之前，插入：

```python
_qg_passed = state.get("_quality_gate_passed")
if _qg_passed is False:
    logger.warning(
        "settlement_extractor_node.qg_false_blocked",
        project_id=state["project_id"],
        chapter_number=state["chapter_number"],
        version_id=version.version_id,
    )
    return {
        "settlement_id": None,
        "summary_id": None,
        "status": "settlement_review",
        "_settlement_needs_human_review": True,
    }
```

**安全说明**：SettlementExtractor 的核心提取算法不变；拦截仅阻止 QG false 版本进入 apply/write/index 流程。

### Step B: Writer Prompt 修正（`writer/1.0.9.yaml`）

替换 L355-368 的 `new_setting_mark` section：

```yaml
  - id: "new_setting_mark"
    name: "新设定标记"
    description: "SettlementExtractor 自动识别新设定，正文禁止任何元标记"
    weight: 1.0
    content: |
      新设定由 SettlementExtractor 自动识别并记录，**禁止**在正文中手动添加任何形式的元数据标记。
      禁止输出：
      - `<!-- 新设定:... -->`
      - `[[新设定:...]]`
      - 任何 HTML 注释或内部工作标记
```

### Step C: Writer 后处理清理（`writer.py`）

在 L459-460 处，将保留注释的逻辑改为强制清理：

```python
    # 去除所有 HTML 注释（兜底清理元标记泄漏）
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # 去除旧版可见标记 [[新设定:...]]（兜底）
    text = re.sub(r"\[\[新设定:[^\]]+\]\]", "", text)
```

### Step D: 单测覆盖

新增或调整测试：

- `test_settlement_extractor_blocks_qg_false`：验证 `_quality_gate_passed=False` 时 settlement 不执行，返回 `settlement_review`。
- `test_writer_strips_html_comments`：验证 `<!-- 新设定:... -->` 被完全移除。
- 更新 `test_phase2_graph` 中涉及 QG false 路径的契约（如有）。

### Step E: 代码检查

```powershell
python -m pytest tests/test_phase2_graph.py tests/test_108_core_nodes.py -q
ruff check src/ tests/
```

---

## 5. 验收标准

- [ ] `settlement_extractor_node` 在 `_quality_gate_passed=False` 时返回 `status="settlement_review"`，不调用 `extract_settlement`、`accept_with_settlement_boundary`、`write_chapter_summary`、RAG 索引和生命周期清理。
- [ ] `writer.py` 后处理后的正文中不含任何 `<!-- ... -->`。
- [ ] `writer/1.0.9.yaml` 不再要求 writer 输出 HTML 注释。
- [ ] 单测覆盖上述两条新契约。
- [ ] `pytest` 全量通过，`ruff` 无报错。

---

## 6. 后续

- Task 121m 完成后，与 Task 121n（预算调整 + human_marks 生命周期）并行或串行推进。
- 两者完成后，执行 Task 121o（Ch1-Ch18 聚焦验证重跑），确认：
  - QG false 版本不再进入 settlement。
  - 正文中无元标记泄漏。
  - 能稳定越过 Ch13 和 Ch18。

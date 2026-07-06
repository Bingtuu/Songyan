# Task 170c: T9 近似/改写重复检测补强

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 量具修复（先行、独立、低风险）
> **优先级**: P0（量具优先——提质复评依赖可信的去重检测）
> **依赖**: 170b DONE（提供 Ch31 漏报样本）
> **状态**: ◻ 规划中

---

## 问题（170b 实证）

170b 抽读发现 Ch31 存在明显重复，但 T9 `duplicate_paragraph_count = 0` —— **漏报**：

- L633 ↔ L641：整段几乎逐字重复（"像一股电流从脊椎底部窜上来，穿过胸腔，在颅骨内壁炸开……现在不是愤怒的时候"）。
- L643 ↔ L659：整句重复（"林渊的指尖在触控板上划动，将七条光谱线的数据分别导出……而是因为他想否认自己看到的东西"）。
- L645：悬空残句"**而是**一种结构化的共鸣……"（缺"不是"前件）。

## 认知修正（查证得到，非从零加）

`detect_duplicate_paragraphs` **已有近似匹配能力**，不是"只抓全等整段"：

- 位置：`src/songyan/agents/rule_auditor.py:149-187`（**全项目唯一实现**；`evals/text_cleanliness.py:8-12` 是 import 复用）。
- 已用 `difflib.SequenceMatcher(...).ratio()`，默认 `similarity_threshold=0.9`、`min_chars=100`。
- 归一化 `_normalize_paragraph_for_similarity`（`:128-130`）：`re.sub(r"\s+", "", paragraph.strip())`（去所有空白）。
- 段落切分 `split_paragraphs`（`utils/_helpers.py:8-15`）：按**单个换行符** `\n` 切，每非空行即一段。
- **只在单章 `text` 内两两比较**，不跨章。

所以 170c 是**诊断漏报根因 + 调参/扩展**，不是从零造模糊匹配。

## Goal

1. 用 Ch31 作回归样本，**先复现并定位漏报根因**（下列假设逐一验证）。
2. 按根因做最小扩展，使其能抓"近似/改写重复"，同时不误伤正常复现（如刻意重复的修辞）。
3. 补单测锁定行为。

## 根因假设（需先验证，不预设结论）

| 假设 | 验证方式 | 若成立的动作 |
|------|----------|--------------|
| A. `similarity_threshold=0.9` 过高，改写重复相似度落在 0.75–0.9 | 对 Ch31 L633/L641 实测 ratio | 下调阈值或分级（≥0.9 major / 0.75–0.9 notice） |
| B. `min_chars=100` 把较短重复段滤掉 | 量 L643/L659 归一化后字数 | 下调 min_chars 或对短段用更高阈值 |
| C. 切分粒度问题：重复内容跨多个"单换行段"，未作为整体比 | 检查 Ch31 重复块的换行结构 | 增加"滑动窗口/多段合并"比较，或按场景段比 |
| D. 归一化去空白后，标点/顺序差异拉低 ratio | 对比归一化前后 ratio | 调整归一化策略 |

> 纪律：**先出根因诊断，再改代码**。不在未复现前盲目降阈值（降过头会误伤正常复现修辞）。

## In Scope

- [ ] 复现脚本/测试：把 Ch31 正文（或其重复片段）作为 fixture，断言当前实现漏报，定位根因。
- [ ] 按诊断结论最小扩展 `detect_duplicate_paragraphs`（阈值分级 / min_chars / 多段窗口，取决于根因）。
- [ ] 保留向后兼容：全等整段仍 100% 检出；正常短段不误伤。
- [ ] 新增单测 `tests/test_170c_near_duplicate.py`：覆盖全等、近似改写（0.75–0.9）、悬空残句相邻重复、正常复现修辞（负样本不误伤）。
- [ ] 确认 `text_cleanliness` 复算链路（`collect_text_cleanliness_metrics`）自动受益（因是同一函数）。

## Out of Scope

- 不做跨章去重（当前仅单章内；跨章是更大工程，另议）。
- 不把去重从"诊断观测"升级为"硬阻断 accept"（保持 T9 report-only 现状；是否阻断由后续决策，不在本任务）。
- 不改生成侧（Writer/RevisionHandler）——去重是检测，不是修复正文。
- 不放宽任何已冻结红线（本任务是**提高**检出能力）。

## 悬空残句（L645）说明

悬空残句"而是……（缺不是）"是**语法断裂**，不属于"重复"范畴。170c 只负责重复检测；残句检测归 LiteraryAuditor 的 `sentence_fragments` 观察类型（170d 评估其是否生效），或后续 RuleAuditor 语法检测，此处仅记录、不在 170c 实现。

## 验证要求

```powershell
python -m pytest tests/test_170c_near_duplicate.py -q
ruff check src/songyan/agents/rule_auditor.py tests/test_170c_near_duplicate.py
python -m pytest tests/ -q   # 全量回归，确认未破坏既有去重/洁净度测试
```

## 验收标准

- [ ] Ch31 重复片段被检出（`duplicate_paragraph_count > 0`）。
- [ ] 根因诊断写入 DONE 文档。
- [ ] 全等整段检出不回退；正常复现修辞不误伤（负样本测试通过）。
- [ ] 全量测试通过、ruff 通过。
- [ ] 产出 `tasks/170c-...-DONE.md`。

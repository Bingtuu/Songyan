# Task 170c: T9 近似/改写重复检测补强 — DONE

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 量具修复（先行、独立、低风险）
> **状态**: ✅ 完成（2026-07-06）
> **依赖**: 170b DONE（提供 Ch31 漏报样本 + 隔离 DB `.tmp/task170b_ch1_ch40.db`）

---

## 结论一句话

Ch31 漏报根因 = **`min_chars=100` floor 把 70–95 字的真实重复段整体滤掉**（假设 B），
与相似度阈值、归一化、切分粒度（假设 A/C/D）无关。改为**分级阈值**后，Ch31 两处
漏报全部检出，且全窗口 Ch1–Ch40 无一误报，反而多揪出 5 章此前被隐藏的重复。

## 根因诊断（先复现，再改代码）

复现脚本 `scripts/repro_170c_ch31_duplicate.py`（只读隔离 DB，实测）：

| 重复对 | 归一化字数 | SequenceMatcher ratio | 旧 floor=100 | threshold=0.9 |
|--------|-----------|----------------------|:------------:|:-------------:|
| 段19↔段23（L633↔L641，近似改写，前缀多"愤怒来得很快，"） | 88 / 95 | **0.9617** | ❌ 被滤 | ✅ 达标 |
| 段24↔段32（L643↔L659，逐字重复） | 70 / 70 | **1.0000** | ❌ 被滤 | ✅ 达标 |

**判定**：两对相似度都已越过 0.9 阈值，**唯一拦路的是 100 字下限**。所以：

- 假设 A（阈值过高）❌ 不成立——ratio 0.96/1.0 远超 0.9。
- 假设 B（min_chars=100 过滤）✅ **成立**——两段归一化 70/88/95 均 < 100，进不了比较循环。
- 假设 C（切分粒度/跨段）❌ 不成立——重复内容各自是完整单段，`split_paragraphs` 已正确切出。
- 假设 D（归一化拉低 ratio）❌ 不成立——归一化后 ratio 反而是 0.96/1.0，未被拉低。

## 修复（最小扩展，不推翻既有能力）

`src/songyan/agents/rule_auditor.py::detect_duplicate_paragraphs` 改为**分级阈值**：

| 归一化长度带 | 阈值 | 依据 |
|-------------|------|------|
| `>= 100`（长段） | `0.9`（原值不变） | 向后兼容，Task 161 长段行为零回退 |
| `[40, 100)`（中段） | `0.95`（更严） | 抓 Ch31 这类近乎逐字的中段重复，同时对 FP 更保守 |
| `< 40` | 直接跳过 | 保护刻意的短句 refrain（"不。""是灭口。"） |

参数化为 `min_chars=40`、`long_paragraph_chars=100`、`short_similarity_threshold=0.95`，
默认值即上表；`long_paragraph_chars` 可注入，便于测试隔离验证分级边界。

> 设计取舍：本检测器不只是 report-only —— `review_merger.py:299` 会把命中转成 `major` 可修订
> patch issue，且 `adaptive_halt.py:183` 把 duplicate_total 计入停机信号。故对 FP 成本敏感，
> 中段用 0.95 严阈而非直接下调到 0.9，宁可漏一点边缘近似，也不误伤正常复现修辞。

## 误报体检（全窗口人工核验）

`scripts/sweep_170c_false_positive.py` 跑 Ch1–Ch40，**8 处命中，逐条人工核验全部为真重复**：

| 章 | 命中 | 性质 |
|---|---|---|
| Ch5 | 1 | 苏晚台词逐字重复（段66↔段118） |
| Ch10 | 2 | "方舟通道完全闭合…"叙述**重复 3 次**（段7/17/69） |
| Ch12 | 2 | 心率监测句 + 通道裂缝句逐字重复 |
| Ch15 | 1 | 苏晚通讯台词逐字重复 |
| Ch31 | 2 | 本任务目标（段19↔23 近似、段24↔32 逐字） |

短 refrain（"不。""是灭口。"，< 40 字）全部正确跳过，**零误报**。

## 附带价值（强化 170b blocker）

170b 报告只发现 Ch31 一处重复。补强后证实：**中段窗口至少 5 章（Ch5/10/12/15/31）
存在此前被 floor 隐藏的重复**，其中 Ch10 同一段叙述重复 3 次。这坐实了 170b 的判断——
"治理指标全 0 ≠ 文本干净"，此前 T9 `duplicate_paragraph_count` 的 0 是**假阴性**，
不是真的没有重复。170g 复评须以补强后的检测器为准。

## 交付物

- 代码：`src/songyan/agents/rule_auditor.py::detect_duplicate_paragraphs`（分级阈值）
- 测试：`tests/test_170c_near_duplicate.py`（7 用例：Ch31 回归 2 + 长段兼容 2 + 负样本 3）
- 诊断脚本：`scripts/repro_170c_ch31_duplicate.py`（根因复现）
- 体检脚本：`scripts/sweep_170c_false_positive.py`（全窗口误报核验）

## 验证结果

```
python -m pytest tests/test_170c_near_duplicate.py -q   → 7 passed
python -m pytest tests/ -q                              → 2421 passed, 2 skipped, 1 xfailed
ruff check（4 个改动/新增文件）                          → All checks passed
```

## 验收对照

- [x] Ch31 重复片段被检出（`duplicate_paragraph_count` 2 > 0）。
- [x] 根因诊断写入本文档（假设 B，含实测数据）。
- [x] 全等整段检出不回退（Task 161 测试全通过）；正常复现修辞不误伤（负样本 + 全窗口体检零误报）。
- [x] 全量测试通过、ruff 通过。
- [x] `text_cleanliness` 复算链路自动受益（同一函数，`evals/text_cleanliness.py:87` import 复用）。

## Out of Scope（保持不变）

- 未做跨章去重（仍单章内）。
- 未把去重从"诊断/可修订"升级为"硬阻断 accept"。
- 未改生成侧。
- 悬空残句（L645）不属重复范畴，归 LiteraryAuditor `sentence_fragments`，170c 不实现。

# Task 171q: Ch200 撞墙定点修复 —— 整段重复 T9 硬红线（去重阈值口径对齐）

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 D1/D3 + §7 主线（`NNNp` 通道）
> **类型**: 撞墙定点修复（阶段 Z 主线，接续 171p/171p2）
> **优先级**: P0（D1 全量 Ch200 的阻塞项）
> **依赖**: 171p/171p2（state_mismatch 假阻塞已解）；T9 冻结口径（Task 165）
> **状态**: ✅ **完成（代码 + 实证复验：T9 dup 8→0）**
> **负责人**: songyan-agent

---

## 结论（先写，供 review）

171p2 解掉 state_mismatch 假阻塞后，小窗口 Ch1-5 表面"完成 5/5、Halt: None"，但**逐条核对放行判据发现真缺陷**：**accepted Ch2（`rev-2-3-e22ea611`）含 8 处逐字重复长段落**（两段各重复 5–6 次，similarity=1.0）。这**违反 Task 171 放行判据 Tier 1「零整段落重复」**（`tasks/171-ch200-long-run.md` L48）与冻结 T9（Task 165：重复长段落数必须为 0）。因此"5/5"并非真正意义上通过本任务放行判据，D1 全量长跑若不修会持续产出 T9 fail 正文。

按本任务"撞墙走 `NNNp` 定点修复、不放宽冻结口径"（L65）纪律，本 task 做**定点修复**：把**分段修订去重助手的 `min_chars` 口径与冻结 T9 检测器对齐**（100→40），使去重实际覆盖 T9 检测器所判的 40–99 字近逐字重复段落。**不放宽任何冻结阈值**（T9 仍要求 =0，只是让确定性去重真正生效到 T9 判定的同一区间）。

**与 171c Goodhart 的关键区别**：171c 证伪的是"把自然对白拆成短引号"以骗过 voice/exposition 量具——指标升、行文碎、质量未升（指标与质量背离）。本 task 删除的是**逐字重复 5–6 次的机械 stutter**——删掉冗余重复段落，指标与真实质量**同向**（没有任何读法偏好同一段落重复 6 次）。这是内容保全的正当去重，非 Goodhart。

---

## 根因（Task 171 小窗口实证）

证据（隔离 DB `.tmp/task171_ch1_ch200.db`）：

| Ch2 版本 | 类型 | dup(min=40) | dup(min=100) |
|---|---|---|---|
| v-2-1 | writer 初稿 | 0 | 0 |
| rev-2-2 | 分段修订 | 6 | 0 |
| rev-2-3 | 分段修订（**accepted**） | 8 | 0 |
| v-2-4 | rewrite（结构完整但缺 ending_hook 被回滚） | 0 | 0 |

- **重复由分段修订引入**：writer 初稿 v-2-1 干净，分段修订 rev-2-2/rev-2-3 反而拼接出逐字重复段落（LLM 分段改写 + 拼接产生 stutter）。
- **两段被重复段的归一化长度 = 49 / 54 字**，落在 `[40, 100)`。
- **口径错配（根因）**：T9 检测器 `detect_duplicate_paragraphs` 用 `min_chars=40`，但去重助手 `_dedup_long_paragraphs`/`_dedup_reassembled_content` 默认 `min_chars=100`——所以去重助手把这两段当"短段"跳过，**永远删不掉**。实测：`_dedup_reassembled_content(content, min_chars=100)` 后检测器仍 8；`min_chars=40` 后检测器 0，正文 4907→4479 字（只删冗余重复，两段**唯一叙事内容各保留 1 份**）。
- **无 accept-time 硬门**：重复长段落经 review_merger 转 `rule-dup-*` major issue 可触发修订，但修订用 LLM 不保证删干净；rewrite 后清 major 标志；quality gate / score card 不读 `duplicate_paragraph_count`；accept 路径无 T9 检查。故 dup 版本可被选为 best + degraded-accept。**本 task 只做最小定点修复（去重口径对齐），不新增 accept 硬门**（避免超 MVP；留后续 task 视需要评估）。

---

## 修复方案（最小定点）

### 主修复：`src/songyan/agents/revision_handler/_segmented_revision.py`
把确定性去重助手的默认口径与冻结 T9 检测器**分级对齐**：
- `_dedup_long_paragraphs(min_chars=100 → 40)`、`_dedup_reassembled_content(min_chars=100 → 40)`。
- **相似度阈值改为分级**（review 采纳）：`[40,100)` 用 **0.95**、`≥100` 用 **0.9**——镜像检测器 `detect_duplicate_paragraphs` 的 `short_similarity_threshold=0.95 / similarity_threshold=0.9` 分级。
  - 依据：检测器在 `[40,100)` 段用 0.95、刻意把 0.90–0.95 的中段对**判为不同段**（`test_170c_near_duplicate.py::...090_095_band_not_flagged`）。若助手在该段用平铺 0.9，会删掉 T9 本就判为"不同"的正当内容——制造与本 bug 镜像的**过度删除**面。分级对齐后：删除区间恰好 = T9 判定区间，既足以驱动 T9→0，又不删 T9 认可的独立段落。

> 依据：冻结 T9 的 `detect_duplicate_paragraphs` 用 `min_chars=40` + 长/中段分级阈值（0.9/0.95）。去重助手对齐到同一下限 + 同一分级阈值，属"让既有确定性去重按 T9 同口径生效"，非新增/放宽判据。

### 不做（明确边界）
- 不改 T9 检测器阈值、不改 T9 =0 冻结口径。
- 不新增 accept-time T9 硬门 / 不改 quality gate score card（超本次最小修复；如需另立 task）。
- 不引入 LLM 去重（超 MVP + 属已封存自动改写闭环）。

> **段落切分差异（review 记录，非阻塞）**：检测器按单换行切分（`split_paragraphs`），助手按空行切分（`re.split(r"\n\s*\n")`）。Ch2 reassembly 以 `\n\n` 拼接故二者单元一致、8→0 复算成立；但"覆盖 T9 所判区间"是**对 Ch2 的实证**，非普遍不变式（嵌在大块内的单行重复助手可能不删）。本次只认 Ch2 实证 + 分级对齐，普遍化留后续。

---

## 测试
- 复用/扩展 `tests/test_161_paragraph_dedup.py`：
  - 新增用例锁定 40–99 字**逐字**重复段落经 `_dedup_reassembled_content`/`_reassemble_content` **默认参数**即被删除（回归防止 min_chars 漂回 100）。
  - **新增中段保留用例**（review 采纳）：镜像 `test_170c_near_duplicate.py::...090_095_band_not_flagged`，断言 `[40,100)` 段 similarity∈[0.90,0.95) 的一对段落经助手默认参数**双双保留**（锁定分级 0.95、防回退平铺 0.9）。
  - 保留既有长段（≥100）去重与短句 refrain（<40）不误删的用例。

## 实证复验
- 对 accepted Ch2 正文用**修复后默认参数**的 `_dedup_reassembled_content` 复算：检测器 dup 8→0，两段唯一叙事内容各保留、正文长度只减冗余。
- 重跑小窗口（`--init` 干净重跑 or 定点重生成 Ch2）验证 accepted 正文 T9 duplicate=0（作为出口证据）。

## 验证要求
```powershell
python -m pytest tests/test_161_paragraph_dedup.py tests/test_079_segmented_revision.py tests/test_170c_near_duplicate.py -q
ruff check src/songyan/agents/revision_handler tests/test_161_paragraph_dedup.py
```

## 出口
- 分段修订路径产出的正文默认去重覆盖 T9 检测区间（40 字起、分级阈值），**分段修订引入的**逐字重复被清除。
- **诚实边界**（review 采纳）：本修复只闭合"分段修订引入 dup"这一已证向量；非分段路径（rewrite / 直接 accept best）仍无 accept-time T9 硬门，如需保证所有 accept 路径 T9=0 须另立 accept 门 task（超本次最小修复）。
- 不放宽 T9/health/orphan/T12 冻结口径；不新增 Agent/节点；无大纲项目行为不变（去重助手仅在分段修订路径生效）。
- D1 全量 Ch200 前置阻塞项（分段修订 T9 撞墙）清除后，方可放全量长跑取真实证据。

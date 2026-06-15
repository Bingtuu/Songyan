# Task 039: 长程架构调研 (Phase 6)

## 状态: ✅ 已完成

---

## 目标

(A) 用随机抽样验证跨章一致性；  
(B) 调研 100+ 章的根本性技术方案，输出 ≥3 种候选架构的评估报告。

---

## 交付物

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 随机一致性测试引擎 | `evals/consistency_test.py` | 5 种测试类型，纯 DB+文本，可复现抽样 |
| 一致性测试报告模型 | `evals/consistency_test.py` | `ConsistencyTestReport` 含加权评分 |
| 一致性测试单元测试 | `tests/evals/test_consistency_test.py` | 20 个测试用例，全部通过 |
| 长程调研脚本 | `scripts/long_range_research.py` | 4 个方案 MVP 实验自动化 |
| 实验数据 | `docs/architecture/long_range_research_data.json` | 方案 A~D 的量化结果 |
| 调研报告 | `docs/architecture/long_range_research_report.md` | 完整报告 + 推荐方案 + 路线图 |

---

## Part A: 随机一致性测试

### 实现

`RandomConsistencyTest` 类提供 3 类测试：

1. **设定一致性**: 从 `setting_tracking` 抽样，检查 `setting_key`/`setting_name` 在后续章节是否被提及
2. **道具追踪**: 从 `inventory_tracker` 抽样，检查 `item_name` 在获得后章节是否出现
3. **伏笔回收**: 检查所有 foreshadowing 的 `resolved`/`overdue` 状态

技术特点:
- 不调用 LLM，纯本地计算
- 可复现抽样 (`random.Random(project_id)`)
- 关键词模糊匹配（精确子串 + Jaccard 滑动窗口）

### 测试覆盖

`tests/evals/test_consistency_test.py`: **20 passed**

| 测试组 | 用例数 | 覆盖点 |
|--------|--------|--------|
| Text scanning | 4 | 精确匹配、空关键词、模糊匹配、相似度计算 |
| Data models | 6 | 加权召回率、综合评分、伏笔回收率 |
| Engine | 8 | 空项目、设定召回、道具追踪、伏笔 resolved/overdue、可复现抽样 |

---

## Part B: 100+ 章长程架构调研

### 数据集

- 文本: 《轨道上的怪谈》Ch2~Ch11 (10 章, 46,505 字)
- 结构化数据: DB 中的 setting_tracking, foreshadowing, inventory_tracker

### 四个候选方案 MVP 结果

| 方案 | 加权总分 | 核心结论 |
|------|---------|---------|
| A 叙事知识图谱 | 4.05 | 实体抽取瓶颈，变体匹配弱 |
| B RAG+分层摘要 | 5.05 | 中文专有名词检索效果一般，需优化 embedding |
| C 专用记忆 LLM | 5.45 | 理论最优，但成本高、幻觉风险、调试困难 |
| D 人类辅助记忆 | **7.55** | **可靠性最高，实现最简单，与现有架构最兼容** |

### 推荐方案

**D + B 混合架构**:
- 以人类辅助记忆 (D) 为可靠性基石
- 以 RAG + 分层摘要 (B) 为自动化扩展层
- ContinuityAuditor 发现 orphaned setting 时自动建议人类标记

### 实施路线图

- **Phase 7 (V2.1.0)**: Human-Augmented Memory 基础 (`human_marks` 表 + CLI + ContextManager 集成)
- **Phase 8 (V2.2.0)**: RAG 自动层 (中文 embedding 评估 + chunking + 检索注入)
- **Phase 9 (V2.3.0)**: 知识图谱补充 (可选，从 settlement 自动生成)

---

## 关键发现 (一致性实证)

在 Ch2~Ch11 数据集中发现典型一致性问题：

1. **"认知校准补丁"**: Ch3 首次出现，Ch4 被提及，**Ch5~Ch11 完全遗忘**
2. **"120Hz 干扰器"**: 文本中分散出现为 "电磁干扰器" + "120 赫兹"，存在**重新发明风险**
3. **实验体代际**: Ch10~Ch11 才大量出现，前 9 章缺乏铺垫，存在**信息跳跃**

---

## 修改文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `evals/consistency_test.py` | 新增 | 随机一致性测试引擎 |
| `tests/evals/test_consistency_test.py` | 新增 | 20 个单元测试 |
| `scripts/long_range_research.py` | 新增 | 调研 MVP 实验脚本 |
| `docs/architecture/long_range_research_report.md` | 新增 | 调研报告 |
| `docs/architecture/long_range_research_data.json` | 新增 | 实验数据 |
| `src/songyan/db/settlement_repo.py` | 修改 | 新增 `list_all()` 方法 |
| `src/songyan/db/repository.py` | 修改 | 新增 `ChapterHeadRepository.list_by_project()` |
| `src/songyan/agents/settlement_extractor.py` | 修改 | P0 修复: `conn` 参数支持调用方事务管理 |
| `src/songyan/workflows/_nodes.py` | 修改 | settlement_extractor_node 传入 `conn` |
| `tests/cli/test_cli.py` | 修改 | 修复 genre 选择序号 (3→7) |

---

## 基线数据

| 指标 | 数值 |
|------|------|
| 测试通过 | **934 passed** (+20 vs 本轮开始) |
| 测试失败 | 6 (预存问题，非本轮引入) |
| ruff (修改文件) | 0 errors |

---

*完成日期: 2026-06-02*  
*关联: Phase 6, STATUS.md 更新, roadmap_v2_phases.md*

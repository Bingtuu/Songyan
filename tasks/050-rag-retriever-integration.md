# Task 050 — RAGRetriever + ContextManager 集成 + Writer Prompt 1.0.6

> **目标**: 将 RAG 检索能力接入创作流水线——构造查询、检索相关段落、注入上下文、渲染到 Writer Prompt，实现长程记忆的自动补充。  
> **Phase**: 8b  
> **优先级**: P0  
> **依赖**: Task 049（Chunker + Embedder + VectorStore）+ Phase 8a（ProjectSetting 扩展）  
> **预计工作量**: 中（2~3 天）

---

## Context

Task 049 实现了 RAG 数据层（切分、向量化、存储）。本 Task 负责**消费**这一层——在章节生成时自动检索相关历史内容，并将结果注入 Writer 的上下文。

**集成点**（来自 `docs/architecture/phase8b_rag_layer.md`）：
1. **Query 构造**: 从 `ChapterGoal.target_events` + `RecentPlot` 构造检索查询
2. **RAGRetriever**: 调用 Embedder 编码 query → VectorStore.search → 返回 `RetrievedChunk[]`
3. **ContextManager**: 将 `RetrievedChunk[]` 转换为 `SoftReference(type="rag_retrieval")`，按优先级注入 `ContextPackage`
4. **Writer Prompt 1.0.6**: 新增 RAG 结果分区，明确标注"仅供参考"

**触发策略**: 
- ≤30 章项目默认不启用（零成本）
- `auto` 模式下，阈值 = `estimated_chapters * 0.3`（如 100 章项目从第 30 章起启用）
- `always` / `never` 由 `RAGConfig.enabled` 控制

---

## Goal

完成 RAG 层与创作流水线的端到端集成：章节生成时自动检索历史相关段落 → 转换为 soft reference → 注入 Writer Prompt，使 Writer 在 30+ 章后仍能回忆起早期关键设定。

---

## In Scope（必须完成）

### 1. RAGRetriever（`src/songyan/rag/retriever.py`）
- [ ] `RAGRetriever` 类
- [ ] `build_query(chapter_goal, recent_plot) -> str` — 从章节目标 + 最近剧情构造检索 query
  - 加权策略：`target_events` 重复一次（利用 mean pooling 自然加权）+ 最近剧情摘要
  - **过滤 obligations 中的元指令**：如 "本章必须精彩"、"节奏不能慢" 等不含实体信息的元指令应排除，避免引入噪声
- [ ] `retrieve(query, top_k, min_similarity) -> list[RetrievedChunk]` — 编码 query → 搜索 VectorStore
- [ ] `retrieve_for_chapter(project_id, chapter_number, chapter_goal, recent_plot)` — 完整封装

### 2. ContextManager 扩展（`src/songyan/agents/context_manager.py`）
- [ ] `SoftReference` 扩展：`type` 新增 `"rag_retrieval"`，新增 `source_chapter` / `similarity` 字段
- [ ] `_build_soft_references()` 中区分 `setting_snapshots` 转换的 soft refs 与 RAG 检索结果
- [ ] 新增 `_load_rag_results(project_id, chapter_number, chapter_goal, recent_plot) -> list[SoftReference]`
- [ ] `assemble_context_package()` 中调用 RAG 加载器（仅在 `should_enable_rag()` 返回 True 时）
- [ ] RAG 结果优先级：`human_marks` > `rag_retrieval` > 时间衰减的 `setting_snapshots`
- [ ] **BudgetPruner 排序策略**: RAG 结果的 `relevance_score` 初始化为 `similarity + 0.3`（确保 RAG 结果在 0.6~1.0 区间，优先于普通 setting snapshots），然后在同一列表内按 `relevance_score` 降序统一裁剪。这样既保证 RAG > snapshot，又保留"高相似度 RAG 结果比低相似度更优先"的精细控制

### 3. RAG 启用判断（`src/songyan/rag/utils.py`）
- [ ] `should_enable_rag(current_chapter, project_setting, rag_config) -> bool`
  - `never` → False
  - `always` → True
  - `auto` → `current_chapter >= (rag_config.threshold_chapters or compute_threshold(project_setting))`
- [ ] `compute_threshold(project_setting) -> int`: `estimated_chapters * 0.3`，最低 10 章，最高 50 章
- [ ] **查询降级策略**: 若 `retrieve()` 返回空（所有结果相似度 < 0.4），降级为对上一章全文做关键词匹配检索，避免 Writer 完全失去自动检索上下文

### 4. Writer Prompt 1.0.6（`prompts/cards/writer/1.0.6.yaml`）
- [ ] 新增 RAG 结果分区：
  ```yaml
  {% if rag_results %}
  ## 历史相关段落（自动检索）
  以下段落来自历史章节，经语义检索判定与当前写作内容相关。
  **注意**：这些段落仅供参考，不要求必须引用。如果与当前章节目标冲突，以章节目标为准。

  {% for chunk in rag_results %}
  - [第{{ chunk.chapter_number }}章 {{ chunk.metadata.chunk_type }}] {{ chunk.text[:200] }}...
  {% endfor %}
  {% endif %}
  ```
- [ ] `creative_mode_profile` 中 `writer_prompt_version` 升级到 `"1.0.6"`
- [ ] 现有 `literary` / `webnovel` / `webnovel_intense` mode 的 prompt 版本同步更新

### 5. CreativeModeProfile 扩展
- [ ] `creative_modes/*.json`: 新增 `rag_config` 字段（使用 Task 049 定义的 `RAGConfig` 默认值）
- [ ] `src/songyan/models/creative_mode.py`: `CreativeModeProfile` 追加 `rag_config: RAGConfig`
- [ ] 向后兼容：旧 mode 文件无 `rag_config` 时，使用默认值 `enabled="auto"`

### 6. 流水线集成（`src/songyan/workflows/`）
- [ ] `src/songyan/workflows/_helpers.py`: `assemble_context_package()` 新增 `rag_retriever: RAGRetriever | None` 参数
- [ ] `src/songyan/workflows/_nodes.py`: `context_manager_node` 中传入 RAGRetriever
- [ ] `src/songyan/workflows/phase1_graph.py`: `Phase1State` 无需修改（RAG 结果通过 ContextPackage 传递）

### 7. CLI 开关
- [ ] `songyan run --rag-mode auto|always|never` — 覆盖 project 默认配置
- [ ] `songyan run --skip-rag` — 快捷禁用 RAG

---

## Out of Scope（明确不做）

- 不修改 Chunker / Embedder / VectorStore（属于 Task 049）
- 不做 embedding 基准测试（属于 Task 048）
- 不做 A/B 质量评估（属于 Task 051）
- 不实现稀疏向量检索优化（后续迭代）
- 不修改 GoalPlanner / CreativeDirector / RuleAuditor（除非必要兼容）
- 不引入新的 LLM 调用（RAG 层零 API 成本）

---

## 接口契约

```python
# src/songyan/rag/retriever.py

class RAGRetriever:
    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        rag_config: RAGConfig,
    ) -> None: ...

    async def retrieve_for_chapter(
        self,
        project_id: str,
        chapter_number: int,
        chapter_goal: ChapterGoal,
        recent_plot: RecentPlot,
    ) -> list[RetrievedChunk]: ...

    def build_query(
        self,
        chapter_goal: ChapterGoal,
        recent_plot: RecentPlot,
    ) -> str: ...


# src/songyan/rag/utils.py

def should_enable_rag(
    current_chapter: int,
    project_setting: ProjectSetting,
    rag_config: RAGConfig,
) -> bool: ...

def compute_rag_threshold(project_setting: ProjectSetting) -> int: ...
```

---

## 数据模型变更

```python
# src/songyan/models/context.py — SoftReference 扩展

class SoftReference(BaseModel):
    type: Literal[
        "world_setting",
        "character_backstory",
        "style_sample",
        "rag_retrieval",      # Phase 8b 新增
    ]
    content: str
    relevance_score: float = 0.0
    source_chapter: int | None = None   # Phase 8b 新增
    similarity: float | None = None      # Phase 8b 新增（RAG 相似度）


# src/songyan/models/creative_mode.py — CreativeModeProfile 扩展

class CreativeModeProfile(BaseModel):
    # ... 现有字段 ...
    rag_config: RAGConfig = Field(default_factory=RAGConfig)
```

---

## 实现清单

### 1. RAG 检索模块
- [ ] `src/songyan/rag/retriever.py`: `RAGRetriever`
- [ ] `src/songyan/rag/utils.py`: `should_enable_rag`, `compute_rag_threshold`

### 2. ContextManager 改造
- [ ] `src/songyan/models/context.py`: `SoftReference` 扩展
- [ ] `src/songyan/agents/context_manager.py`: `_load_rag_results()` + `assemble_context_package()` 集成

### 3. Prompt 升级
- [ ] `prompts/cards/writer/1.0.6.yaml`: 新建 Writer Prompt
  - **必须**在底部 `variables` 部分注册 `rag_results` 变量及其类型（`list[RetrievedChunk] | None`）和必填性（`false`），否则 PromptLoader 渲染时会校验失败
  - **区块顺序**（注意力链条）：硬约束 → 章节目标 → **RAG 检索结果** → 风格参考/分层摘要 → 题材规则。RAG 放在章节目标之后、风格参考之前，形成"先知道必须写什么 → 再看历史上相关段落怎么写 → 最后看风格样本"的清晰链条
- [ ] `creative_modes/*.json`: 更新 `writer_prompt_version` 为 `"1.0.6"`，新增 `rag_config`

### 4. 模型层
- [ ] `src/songyan/models/creative_mode.py`: `rag_config` 字段

### 5. 流水线
- [ ] `src/songyan/workflows/_helpers.py`: `assemble_context_package` 传入 RAGRetriever（**注意**: pipeline 实际调用的是 `_helpers.py` 中的版本，`context_manager.py` 中的同名函数为内部实现或已废弃，需确认后统一修改入口）
- [ ] `src/songyan/workflows/_nodes.py`: `context_manager_node` 集成

### 6. CLI
- [ ] `src/songyan/cli/commands/run.py`: `--rag-mode` / `--skip-rag` 参数

---

## 测试要求

### Layer 1: 模型测试
- [ ] `test_soft_reference_rag_type`: `type="rag_retrieval"` 可正确序列化
- [ ] `test_rag_config_in_creative_mode`: `CreativeModeProfile` 包含默认 `RAGConfig`
- [ ] `test_rag_config_backward_compat`: 旧 JSON 文件无 `rag_config` 时解析成功

### Layer 2: 模块测试
- [ ] `test_build_query`: 给定 `ChapterGoal` + `RecentPlot`，query 包含 target_events（加权）和 obligations
- [ ] `test_should_enable_rag_never`: 永远返回 False
- [ ] `test_should_enable_rag_always`: 永远返回 True
- [ ] `test_should_enable_rag_auto`: 阈值计算正确（estimated_chapters * 0.3）
- [ ] `test_compute_rag_threshold_bounds`: 最低 10 章，最高 50 章
- [ ] `test_retriever_mock_search`: Mock Embedder + Mock VectorStore，验证 retrieve 流程正确

### Layer 3: ContextManager 测试
- [ ] `test_context_package_includes_rag`: RAG 启用时，`soft_references` 包含 rag_retrieval 类型
- [ ] `test_context_package_skips_rag_when_disabled`: RAG 禁用时，无 rag_retrieval
- [ ] `test_rag_priority_ordering`: RAG 结果的 `relevance_score` 高于普通 setting snapshot（验证 `similarity + 0.3` 策略）
- [ ] `test_budget_pruner_rag_refs`: RAG soft refs 受 BudgetPruner 约束，超预算时按 relevance_score 排序裁剪
- [ ] `test_rag_fallback_to_keyword`: 当 RAG 检索返回空时，验证降级到关键词匹配
- [ ] `test_rag_query_filters_meta_instructions`: 验证 build_query 排除了 obligations 中的元指令（如"必须精彩"）
- [ ] `test_prompt_variables_registered`: PromptLoader 能正确识别 1.0.6.yaml 中的 `rag_results` 变量

### Layer 4: 集成测试
- [ ] `test_end_to_end_rag_injection`: Mock 所有外部依赖，验证 pipeline 从 `context_manager_node` 到 Writer Prompt 渲染的完整链路
- [ ] `test_prompt_1_0_6_rendering`: Jinja 模板渲染包含 RAG 分区，格式正确

---

## 验收标准

- [ ] `pytest tests/rag/test_retriever.py -v` 全部通过
- [ ] `pytest tests/test_context_manager.py -v` 全部通过（含新增 RAG 相关用例，无回归）
- [ ] `pytest tests/creative_modes/ -v` 全部通过（Prompt 版本更新无回归）
- [ ] `pytest tests/integration/ -v` 全部通过（流水线集成无回归）
- [ ] Writer Prompt 1.0.6 可正确渲染，RAG 分区仅在 `rag_results` 非空时显示
- [ ] `--skip-rag` CLI 参数有效，运行时零 embedding 计算
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 更新了 `docs/STATUS.md`（Task 050 状态改为 ✅，组件版本更新为 Writer 1.0.6 / ContextManager 1.0.6）
- [ ] 生成了 `tasks/050-rag-retriever-integration-DONE.md` 交接文件

---

## 已知限制与风险

| 风险 | 说明 | 应对 |
|------|------|------|
| RAG 引入无关段落 | 语义检索可能返回不相关 chunk | `min_similarity=0.3` + `max_results=5` + Prompt 明确"仅供参考" |
| Prompt 变长导致 budget 超标 | RAG 结果增加 token 消耗 | BudgetPruner 已有裁剪逻辑；RAG soft refs 优先级低于 human marks |
| Query 构造不当 | target_events 过于笼统，检索结果泛化 | 先用简单加权策略，Task 051 中根据 A/B 结果调优 |
| 旧 mode 文件兼容性 | 现有 `creative_modes/*.json` 无 `rag_config` | Pydantic `default_factory` 自动补全 |

---

## 参考文档

- `docs/architecture/phase8b_rag_layer.md` — Phase 8b 完整设计文档
- `tasks/049-chunker-embedder-vector-store.md` — Task 049 数据层
- `src/songyan/agents/context_manager.py` — ContextManager 现有实现
- `src/songyan/workflows/_nodes.py` — Pipeline 节点
- `prompts/cards/writer/1.0.5.yaml` — 现有 Writer Prompt（升级基础）

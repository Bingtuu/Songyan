# Songyan 多 AI 协作上下文管理方案

> 目标：让多个 AI 实例分步协作开发时，每个 AI 的上下文窗口都保持在可控范围内，同时不丢失关键信息。

---

## 1. 问题：为什么需要上下文管理？

AI 的上下文窗口有限（通常 200K tokens）。当多个 AI 分步开发一个复杂系统时，每个 AI 需要：
1. 了解项目全局架构（技术方案）
2. 了解当前进度（状态看板）
3. 了解当前任务的规格（Task 文件）
4. 了解上游任务的输出（交接文件）

如果不加管理，一个 AI 在 Phase 4 时需要读前 15 个 Task 的全部代码，上下文立刻爆炸。

---

## 2. 核心原则：分层加载 + 按需裁剪

### 2.1 文档分层（固定开销，每次必加载）

| 文档 | 大小 | 加载方式 |
|------|------|----------|
| AGENTS.md | ~5K tokens | **每次启动必加载**（全局约束） |
| development-tech-plan-v2.md | ~8K tokens | **每次启动必加载**（架构层） |
| ai-collaboration-guide.md | ~4K tokens | 首次参与时加载，后续可选 |
| docs/STATUS.md | ~1K tokens | **每次启动必加载**（状态看板） |
| docs/INDEX.md | ~0.5K tokens | 首次参与时加载 |

**固定开销合计：~10-15K tokens**（AGENTS.md + 技术方案 + STATUS.md）

### 2.2 任务层（按需加载，只加载当前相关）

| 文档 | 大小 | 加载方式 |
|------|------|----------|
| 当前 Task 规格 | ~2-5K tokens | **每次启动必加载** |
| 上游 Task DONE.md | ~1-3K tokens | **有依赖时加载** |
| docs/architecture/04-vibe-coding-engineering.md | ~20K tokens | **需要 Task 详情时加载**（按需） |

**任务层合计：~3-8K tokens**（通常只加载当前 Task + 1-2 个上游 DONE）

### 2.3 代码层（按需加载，不读无关代码）

| 场景 | 加载策略 |
|------|----------|
| **Phase 1（基础设施）** | 只读当前 Task 相关文件，不读其他 Phase 的代码 |
| **Phase 2（写前管线）** | 加载已完成的 Phase 1 代码（models、db、repository）作为依赖，不读 Phase 3-4 |
| **Phase 3（审查修订）** | 加载 Phase 1-2 的输出接口，不读具体实现细节 |
| **Phase 4（结算闭环）** | 加载全部前置接口，按需深入具体实现 |

**关键规则**：
- AI 只读**自己 Task 需要调用的接口**，不读无关实现
- 通过 `import` 和类型标注了解依赖，不读依赖的完整源码
- 需要深入了解时才读具体实现（如 debug 时）

---

## 3. "先读后做"启动协议的上下文预算

```python
@dataclass
class AgentContextBudget:
    """AI 启动时的 Token 预算分配"""
    
    total_budget: int = 128_000           # 总上下文窗口
    
    # 固定开销（必读）
    claude_md: int = 5_000                # AGENTS.md
    tech_plan: int = 8_000                # V2 技术方案
    status_md: int = 1_000                # STATUS.md
    
    # 任务层（当前相关）
    current_task: int = 5_000             # 当前 Task 规格
    upstream_done: int = 3_000            # 上游交接文件
    
    # 代码层（按需）
    related_code: int = 20_000            # 当前 Task 相关代码
    dependency_interfaces: int = 10_000   # 依赖模块的接口（类型标注）
    
    # 预留
    generation_reserve: int = 76_000      # LLM 生成空间
```

**实际使用策略**：
- 启动时先加载固定开销（~14K）+ 当前 Task（~5K）= ~19K
- 根据 Task 需要，选择性加载上游 DONE（~3K）和依赖接口（~10K）
- 如果需要读大量代码，先通过 `grep`/`glob` 定位关键文件，只读相关部分
- 避免一次性加载整个 `src/` 目录

---

## 4. 交接文件的上下文裁剪

### 4.1 DONE.md 的结构化设计

交接文件不应该是代码的完整复制，而是**接口契约 + 关键决策 + 验证方式**：

```markdown
# Task 00X: XXX — 交接报告

## 接口契约（其他 AI 只需要读这部分）
- `xxx.function_name(arg: Type) -> ReturnType` — 功能简述
- `xxx.ClassName.method()` — 关键方法

## 改了哪些文件（索引，不贴代码）
- `src/songyan/xxx/yyy.py` — 新增 ZZZ 功能（200 行）

## 关键设计决策（必须知道）
- 选择了 ABC 而不是 DEF，原因是 GHI

## 如何验证（3 个核心测试命令）
```bash
pytest tests/test_xxx.py::test_case_1 -v
pytest tests/test_xxx.py::test_case_2 -v
pytest tests/test_xxx.py::test_case_3 -v
```

## 已知问题 / 限制
- XXX 场景未覆盖，留给 Task 00Y
```

**DONE.md 大小目标：~1-3K tokens**（只含接口契约和关键决策，不含完整代码）

### 4.2 代码引用策略

当交接文件需要引用代码时，只引用**接口定义**，不引用完整实现：

```python
# 好：只给接口
async def define_chapter_goal(
    project_id: str,
    chapter_number: int,
    db: Repository,
) -> ChapterGoal:
    """制定章节目标。返回结构化 ChapterGoal。"""
    ...

# 不好：给完整实现（占用上下文）
async def define_chapter_goal(project_id: str, chapter_number: int, db: Repository) -> ChapterGoal:
    project = await db.projects.get(project_id)
    characters = await db.characters.list_by_project(project_id)
    # ... 50 行实现细节 ...
```

---

## 5. 减少上下文冗余的机制

### 5.1 类型即文档

通过完整的 Pydantic 模型和类型标注，让 AI 通过类型系统理解接口，不需要读大量文档：

```python
class ChapterGoal(BaseModel):
    """章节目标——GoalPlanner 的输出"""
    chapter_number: int
    target_events: list[str] = []      # 1-3 个关键事件
    emotional_arc: str = ""            # 情感走向
    hooks: list[str] = []              # 章末钩子
    obligations: list[str] = []        # 必须兑现的承诺
    word_count_target: int = 3000
    chapter_type: str = ""             # 从 GenreProfile.chapter_types 选
```

### 5.2 任务粒度控制

每个 Task 文件控制在 **200-500 行**（~2-5K tokens），只包含：
- Goal（一句话）
- In Scope（列表）
- Out of Scope（列表）
- Acceptance Criteria（可验证的 checklist）

不包含：完整设计文档、完整代码示例、冗长的背景说明。

### 5.3 STATUS.md 的精简

状态看板只保留：
- 当前阶段（1 行）
- 已完成列表（任务名）
- 进行中（1 个任务）
- 待开始列表（任务名）
- 阻塞项（如有）
- 最近变更（3-5 条）

不保留：完整的技术讨论、设计决策记录、已解决的历史问题。

---

## 6. 调试时的上下文扩展

当 AI 遇到 bug 需要深入代码时，可以临时扩展上下文：

1. **先用 grep 定位**：`grep -r "function_name" src/` 找到相关文件
2. **只读相关文件**：不读整个目录，只读包含问题的 1-3 个文件
3. **读关键部分**：用行号范围只读相关函数，不读完整文件
4. **验证后释放**：debug 完成后，回到正常上下文预算

---

## 7. 总结：上下文管理口诀

```
启动三件套：CLAUDE + 方案 + 状态板（~15K）
当前任务要加载：Task 规格 + 上游 DONE（~5K）
代码按需不贪婪：接口优先，实现必要时才读（~10-20K）
交接文件要精简：接口契约 + 关键决策 + 验证方式（~2K）
调试按需扩窗口：grep 定位 → 只读相关 → 验证后释放
```

**目标**：每个 AI 实例的常驻上下文控制在 **30-40K tokens** 以内，预留 80K+ 用于代码生成和推理。

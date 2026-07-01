# Task 069a: 分层摘要 — 数据层对齐与生成器

> **Phase**: V3.1 — 质量跃迁
> **优先级**: P1
> **依赖**: 无（与 067/068 可并行，但本 Task 是 budget 根本解的上半部分）
> **预计工作量**: ~1 天（6-8 小时）

---

## Goal

实现对齐后的 `ArcSummary` / `VolumeSummary` 数据层，并完成调用 LLM 的摘要生成器（`ArcSummaryGenerator` + `VolumeSummaryGenerator`），为 069b 的系统集成提供可复用的生成能力。

## Context

Phase 4 已预留分层上下文基础设施：

| 组件 | 状态 | 说明 |
|------|------|------|
| `ArcSummary` / `VolumeSummary` 模型 | ⚠️ 存在但字段需对齐 | `models/context.py` 中定义，缺 `project_id`，部分字段与 069 规格不一致 |
| `arc_summaries` / `volume_summaries` 表 | ✅ 已存在 | `schema.sql` + `migrations.py` 已创建 |
| `ArcSummaryRepository` / `VolumeSummaryRepository` | ⚠️ 基础实现 | `layered_context_repo.py` 中有 create/get/list，缺 update/delete |
| `load_arc_context` / `load_volume_context` | ✅ 已存在 | `_helpers.py` 中已调用，但 DB 中无实际数据 |
| 生成器 | ❌ 不存在 | 本 Task 核心产出 |

---

## In Scope（必须完成）

### 1. 数据模型对齐

- [ ] 检查 `ArcSummary` / `VolumeSummary` 模型字段与 DB 表、`tasks/069` 规格的兼容性
- [ ] 如需调整：最小化修改（不删除已有字段，只新增缺失字段如 `project_id`）
- [ ] 确保 `model_dump()` / `model_validate()` 与 DB JSON 序列化兼容

### 2. Repository 补全

- [ ] `ArcSummaryRepository`：补充 `update()`、`delete_by_project()`、`get_by_arc_id()`
- [ ] `VolumeSummaryRepository`：补充 `update()`、`delete_by_project()`、`get_by_volume_id()`
- [ ] 所有写入操作记录 structlog

### 3. 弧边界划分规则

- [ ] 实现 `ArcBoundaryResolver`：
  - 优先读取 `project.arc_boundaries`（JSON 数组）
  - 若无配置，自动按 10 章分组
- [ ] 单元测试：有配置时按配置分，无配置时按 10 章分

### 4. ArcSummaryGenerator

- [ ] 读取 `start_chapter` 到 `end_chapter` 的所有章级摘要（`SummaryRepository`）
- [ ] 构建 Prompt（工艺卡：`prompts/cards/arc_summary_generator/1.0.0.yaml`）
- [ ] 调用 LLM，输出约 500 字的弧级摘要
- [ ] 解析并返回 `ArcSummary`
- [ ] 通过 `ArcSummaryRepository.create()` 写入 DB

### 5. VolumeSummaryGenerator

- [ ] 读取项目的所有 `ArcSummary`
- [ ] 构建 Prompt（工艺卡：`prompts/cards/volume_summary_generator/1.0.0.yaml`）
- [ ] 调用 LLM，输出约 300 字的全篇摘要
- [ ] 解析并返回 `VolumeSummary`
- [ ] 通过 `VolumeSummaryRepository.create()` 写入 DB

### 6. 测试

- [ ] Repository 测试：create → get → update → list 完整 CRUD
- [ ] `ArcBoundaryResolver` 测试
- [ ] Mock LLM 测试：生成器输入输出格式正确
- [ ] 回归测试：`pytest tests/ -x -q` 通过（排除已知环境问题）

## Out of Scope（069b 做）

- ContextManager 的分层加载逻辑修改
- SettlementExtractor 的触发逻辑
- 端到端 pipeline 验证（Ch30 token 数）

## 接口契约

```python
class ArcBoundaryResolver:
    def resolve(self, chapter_number: int, arc_boundaries: list[int] | None = None) -> tuple[int, int]:
        """返回当前章所属的 (start_chapter, end_chapter)."""

class ArcSummaryGenerator:
    async def generate(self, project_id: str, start_chapter: int, end_chapter: int) -> ArcSummary: ...

class VolumeSummaryGenerator:
    async def generate(self, project_id: str, arc_summaries: list[ArcSummary]) -> VolumeSummary: ...
```

## 验收标准

- [ ] `pytest tests/test_layered_context_repo.py` 或新增测试文件全部通过
- [ ] Mock LLM 下生成器能在 5 秒内返回格式正确的 ArcSummary / VolumeSummary
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/069a-layered-summary-generators-DONE.md`

## 参考

- `src/songyan/db/layered_context_repo.py` — 现有 Repository
- `src/songyan/models/context.py` — 现有模型
- `tasks/031-layered-context-DONE.md` — V2.x 分层上下文设计

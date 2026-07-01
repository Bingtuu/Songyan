# Task 037: Style Mimicry Engine

> **Phase**: Stage B — Phase 5（Genre 框架增强）
> **优先级**: P0
> **依赖**: Task 035（GenreProfile 模型升级）
> **预计工作量**: 中

---

## Goal

激活 `reference_works` 字段，实现从参考作品中提取风格样本并注入上下文，使 Writer 能模仿特定风格。

## Context

`GenreProfile` 和 `ProjectSetting` 都有 `reference_works` 字段，但从未使用。Style Mimicry Engine 将解析这些参考作品，提取风格特征（句式节奏、描写密度、对话风格、词汇偏好），作为 `SoftReference` 注入 `ContextPackage`。

## In Scope

- [ ] **StyleSample 模型**：
  - `work_name` / `author` / `excerpt`（200~500 字代表性段落）
  - `analysis`（风格特征分析：句式节奏、描写密度、对话风格、词汇偏好）
  - `genre_tags` / `confidence`（0.0~1.0）
- [ ] **StyleMimicryEngine**：
  - `extract_style_sample(reference_work: str) -> StyleSample`：
    - 输入：作品名或文本片段
    - 如果输入是作品名（如"三体"），从内置知识库返回预置 StyleSample
    - 如果输入是文本片段，用启发式规则提取风格特征
    - 输出：`StyleSample`
  - `inject_into_context(style_sample, context_package) -> ContextPackage`：
    - 将 `StyleSample` 包装为 `SoftReference`（type="style_sample"）
    - 注入 `ContextPackage.soft_references`
    - 设置 `relevance_score=0.9`（高优先级）
- [ ] **内置风格样本库**（5 个预置）：
  - 刘慈欣《三体》：硬科幻风格（简洁、概念密集、宏观视角）
  - 金庸《射雕英雄传》：武侠风格（古韵、动作描写、对话机智）
  - 马伯庸《长安十二时辰》：历史悬疑风格（紧凑、细节密集、多线叙事）
  - 刘慈欣《流浪地球》：末日科幻风格（冷峻、集体主义、技术细节）
  - 烽火戏诸侯《雪中悍刀行》：玄幻风格（诗意、江湖气、人物群像）
- [ ] **ContextManager 集成**：
  - 在 `assemble_context_package()` 中，如果 `project.reference_works` 非空，
    - 对每个 reference_work 调用 `extract_style_sample()`
  - 将提取的 style samples 注入 `soft_references`

## Out of Scope

- 不调用 LLM 实时分析文本片段（保持测试可控，使用启发式规则或预置库）
- 不爬取网络数据获取作品全文
- 不修改 Writer 的 prompt 渲染逻辑（B4 负责）
- 不实现真正的风格迁移模型（仅做风格特征注入）

## 接口契约

```python
class StyleSample(BaseModel):
    work_name: str
    author: str = ""
    excerpt: str = ""  # 200~500 字
    analysis: str = ""  # 风格特征分析
    genre_tags: list[str] = Field(default_factory=list)
    confidence: float = 0.0

class StyleMimicryEngine:
    def __init__(self) -> None:
        self._builtin_samples: dict[str, StyleSample] = {}
        self._load_builtin_samples()

    def extract_style_sample(self, reference_work: str) -> StyleSample | None:
        ...

    def inject_into_context(
        self,
        style_sample: StyleSample,
        ctx: ContextPackage,
    ) -> ContextPackage:
        ...
```

## 测试要求

### Layer 1: 模型测试
- [ ] `StyleSample` 可正确实例化
- [ ] 内置库包含 5 个预置样本

### Layer 2: 模块测试
- [ ] `extract_style_sample("三体")` 返回预置样本
- [ ] `extract_style_sample("未知作品")` 返回 None 或 fallback
- [ ] `inject_into_context` 正确添加到 `soft_references`
- [ ] 不影响无 `reference_works` 的项目的上下文组装

### Layer 3: 集成测试
- [ ] ContextManager 组装时自动注入 style samples

## 验收标准

- [ ] 可从参考作品提取风格样本（预置库或启发式）
- [ ] 风格样本能正确注入 `ContextPackage.soft_references`
- [ ] 不影响无 `reference_works` 的项目的上下文组装
- [ ] 所有现有测试继续通过
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/037-style-mimicry-engine-DONE.md`

## 参考

- `docs/architecture/roadmap_v2_phases.md` — Phase 5.3
- `src/songyan/models/context.py` — SoftReference
- `src/songyan/agents/context_manager.py`

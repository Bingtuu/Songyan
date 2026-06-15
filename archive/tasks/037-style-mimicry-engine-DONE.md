# Task 037 DONE 报告：风格模仿引擎

> **完成日期**: 2026-06-02
> **执行人**: Kimi Code CLI
> **任务**: Task 037 — Style Mimicry Engine（Stage B Phase 5.3）

---

## 交付摘要

激活 `reference_works` 字段，实现从参考作品提取风格样本并注入 `ContextPackage.soft_references`，使 Writer 能在 prompt 中感知目标风格。

---

## 修改清单

### 1. 模型层 (`src/songyan/models/style_mimicry.py`)

新增 `StyleSample` 模型：

| 字段 | 类型 | 说明 |
|------|------|------|
| `work_name` | str | 作品名 |
| `author` | str | 作者 |
| `excerpt` | str | 200~500 字代表性段落 |
| `analysis` | str | 风格特征分析（句式节奏/描写密度/对话风格/词汇偏好）|
| `genre_tags` | list[str] | 风格标签 |
| `confidence` | float | 0.0~1.0，预置样本 ≥ 0.88 |

### 2. 引擎层 (`src/songyan/agents/style_mimicry_engine.py`)

**StyleMimicryEngine** 核心方法：

- `extract_style_sample(reference_work: str) -> StyleSample | None`
  - 作品名精确匹配内置库 → 返回预置样本
  - 作品名带《》 → 去书名号后匹配
  - 文本片段（>50 字） → 启发式提取（平均句长、对话比例分析）
  - 未知作品名或短文本 → 返回 None

- `inject_into_context(style_sample, ctx) -> ContextPackage`
  - 将 `StyleSample` 包装为 `SoftReference(type="style_sample", relevance_score=0.9)`
  - 追加到 `ctx.soft_references`

- `inject_multiple(style_samples, ctx) -> ContextPackage`
  - 批量注入

**内置风格样本库（5 个）**：

| 作品 | 作者 | 风格关键词 | confidence |
|------|------|-----------|------------|
| 三体 | 刘慈欣 | 硬科幻、简洁、概念密集、宏观视角 | 0.95 |
| 射雕英雄传 | 金庸 | 武侠、古韵、动作描写、对话机智 | 0.95 |
| 长安十二时辰 | 马伯庸 | 历史悬疑、紧凑、细节密集、多线叙事 | 0.90 |
| 流浪地球 | 刘慈欣 | 末日科幻、冷峻、集体主义、技术细节 | 0.92 |
| 雪中悍刀行 | 烽火戏诸侯 | 玄幻、诗意、江湖气、人物群像 | 0.88 |

### 3. ContextManager 集成 (`src/songyan/agents/context_manager.py`)

- `assemble_context_package()` 新增 `style_samples: list[StyleSample] | None = None` 参数
- 在 `ContextPackage` 构建后、BudgetPruner 裁剪前，自动调用 `StyleMimicryEngine.inject_multiple()` 注入
- 无 `style_samples` 时不影响现有逻辑

### 4. 导出更新 (`src/songyan/models/__init__.py`)

新增 `StyleSample` 导出。

---

## 测试

新增 `tests/test_style_mimicry_engine.py`（17 个测试）：

**Layer 1 — 模型测试 (3)**:
- StyleSample 最小/完整实例化
- confidence 范围验证

**Layer 2 — 模块测试 (12)**:
- 内置库包含 5 个样本，confidence 均 ≥ 0.8
- extract_style_sample("三体") 返回预置样本
- extract_style_sample("《三体》") 去书名号匹配
- extract_style_sample("未知") 返回 None
- 文本片段启发式提取（平均句长、对话比例分析）
- 短文本返回 None
- inject_into_context 添加 soft_reference，type="style_sample"，relevance_score=0.9
- inject_multiple 批量注入 2 个

**Layer 3 — 集成测试 (3)**:
- assemble_context_package 带 style_samples → soft_references 包含风格样本
- assemble_context_package 不带 style_samples → 无 style_sample 类型引用
- 模拟 project.reference_works 提取并注入 2 个样本

---

## 验证结果

```
tests/test_style_mimicry_engine.py  — 17 passed
tests/test_layered_context.py       — 19 passed
ruff                                 — 0 errors（新增文件）
```

---

## 向后兼容

- `assemble_context_package()` 新增可选参数 `style_samples=None`，不破坏现有调用
- 无 `style_samples` 时，ContextPackage 的 `soft_references` 完全不受影响
- `SoftReference.type` 的 Literal 已包含 `"style_sample"`（Task 035 之前已定义）

---

## 已知限制

- 内置样本库仅 5 个作品，覆盖有限；未知作品返回 None
- 启发式提取基于简单统计（平均句长、对话比例），精度有限
- 风格样本注入后，Writer Prompt 中尚未渲染 `soft_references` 的 `style_sample` 类型（B4 负责）
- `reference_works` 字段目前在 GenreProfile 和 ProjectSetting 中均有定义，但引擎优先从项目层消费

---

## 下一步

**Task 038** — Writer Prompt 风格注入（在 Writer Prompt 中新增"风格参考"分区，激活 soft_references 中的 style_sample 渲染）

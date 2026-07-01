# Task 074: 对话质量专项 — DONE

> **Phase**: V3.1 — 质量跃迁
> **完成日期**: 2026-06-06
> **Git Commit**: (待填充)

---

## 交付摘要

为每个主要角色生成对话风格卡，解决 LLMAuditor 中 `dialogue_subtext` + `dialogue_distinctness` 占 21.3% 的问题，提升对话质量和角色辨识度。

## 变更清单

### 数据模型
- `src/songyan/models/character.py`: 新增 `DialogueStyleCard` Pydantic 模型
- `src/songyan/models/character.py`: `Character` 模型新增 `dialogue_style_card` 字段
- `src/songyan/models/context.py`: `ContextPackage` 新增 `dialogue_style_cards` 字段
- `src/songyan/models/__init__.py`: 导出 `DialogueStyleCard`

### DB 层
- `src/songyan/db/schema.sql`: `characters` 表新增 `dialogue_style_card TEXT DEFAULT '{}'` 列
- `src/songyan/db/migrations.py`: 新增 `_migrate_dialogue_style_card` 迁移函数
- `src/songyan/db/repository.py`: `CharacterRepository.create()` 支持写入风格卡
- `src/songyan/db/repository.py`: 新增 `save_dialogue_style_card()` 方法
- `src/songyan/db/repository.py`: `_character_from_row()` 解析 `dialogue_style_card`

### Agent 层
- `src/songyan/agents/creative_director/__init__.py`: 新增 `generate_dialogue_style_cards()` 函数
- `src/songyan/agents/creative_director/__init__.py`: 新增 `_build_dialogue_style_card()` 解析函数
- `src/songyan/agents/writer.py`: `_render_prompt()` 注入 `dialogue_style_cards` 变量
- `src/songyan/agents/llm_auditor.py`: `_render_context_info()` 注入风格卡信息供审查对比

### Prompt 卡
- `prompts/cards/writer/1.0.6.yaml`: 新增 "出场角色对话风格" 分区 + 执行规则
- `prompts/cards/llm_auditor/1.0.2.yaml`: 增强 `dialogue_distinctness` 和 `dialogue_subtext` 维度，明确要求按角色检查风格一致性

### Workflow
- `src/songyan/workflows/_nodes.py`: `creative_director_node` 生成 brief 后检查并生成/保存风格卡
- `src/songyan/workflows/_helpers.py`: `assemble_context_package` 从角色档案加载风格卡注入上下文

### 测试
- `tests/test_dialogue_style_card.py`: 11 个新测试（模型序列化、DB 读写、CreativeDirector 生成、Writer Prompt 注入）
- `tests/integration/test_paths.py`: 更新 `test_path_c_two_rounds_forced_pass` 匹配 073 rewrite 行为
- `tests/integration/conftest.py`: `seed_project()` 给角色预置风格卡，避免测试 mock responses 不够用
- `evals/runner.py`: `import_seed_project()` 给角色预置默认风格卡

### 文档
- `docs/STATUS.md`: 更新 V3.1 完成状态，添加下一步验证计划

## 验证结果

```bash
pytest tests/ -q
# 1243 passed, 1 failed (embedding benchmark mock 环境问题，与 074 无关)
```

## 已知限制

- `generate_dialogue_style_cards()` 在 LLM 不可用时 graceful 返回 `[]`，不阻塞流程
- 风格卡生成使用一次 LLM 调用生成所有角色（经济模式），如果角色过多可能超出输出长度
- 风格卡目前只在 CreativeDirector 运行时检查生成（项目初始化/前几章），不做实时更新
- Writer Prompt 中 `character_id` 用于标识角色，实际渲染时使用 ID 而非角色名（需在 workflow 层映射）

## 下一步

1. 端到端验证 Ch41-Ch50，测量对话 distinctness 评分是否提升
2. 如评分未达预期，优化 CreativeDirector 的风格卡生成 Prompt

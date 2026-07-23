# Task 074: 对话质量专项

> **Phase**: V3.1 — 质量跃迁
> **优先级**: P3
> **依赖**: 无
> **预计工作量**: 大（~2-3 天）

---

## Goal

为每个主要角色生成对话风格卡，解决 LLMAuditor 中 `dialogue_subtext` + `dialogue_distinctness` 占 21.3% 的问题，提升对话质量和角色辨识度。

## Context

058b 数据分析：
- `dialogue_subtext` + `dialogue_distinctness` 占全部 issues 的 21.3%
- 主要问题：
  - 所有角色说话方式相似，缺乏个性
  - 对话缺乏潜台词，过于直白
  - 反派和主角的语气没有明显区分

当前系统的对话质量完全依赖 Writer Prompt 中的通用提示（"对话要有潜台词"），没有针对每个角色的个性化指导。

对话风格卡方案：
- 为每个主要角色（protagonist + antagonist + 关键配角）生成一张对话风格卡
- 风格卡包含：口头禅、句式偏好、情绪表达方式、沉默/停顿习惯、方言/古语特征
- 风格卡由 `CreativeDirector` 在生成 `CreativeBrief` 时一并产出
- Writer Prompt 中注入当前出场角色的风格卡

## In Scope（必须完成）

- [ ] 设计 `DialogueStyleCard` 数据模型
- [ ] 设计风格卡生成 Prompt（由 CreativeDirector 调用 LLM 生成）
- [ ] 修改 `CreativeDirector._build_creative_brief()`：为每个主要角色生成风格卡
- [ ] 修改 `Writer` 的 Prompt 组装逻辑：注入出场角色的风格卡
- [ ] 修改 `LLMAuditor` 的对话审查维度：按角色检查风格一致性
- [ ] DB schema 迁移：新增 `dialogue_style_cards` 表或扩展 `characters` 表
- [ ] 补充单元测试和集成测试
- [ ] 回归测试：`pytest tests/ -x -q` 全部通过

## Out of Scope（明确不做）

- 不做实时对话风格更新（风格卡在项目初始化或角色创建时生成）
- 不做多角色同时对话的复杂场景（先解决 1v1 对话）
- 不做语音/方言的拼音标注（纯文本风格描述）
- 不做对话风格的外部导入（只由 CreativeDirector 生成）

## 数据模型

```python
class DialogueStyleCard(BaseModel):
    character_id: str
    project_id: str
    
    # 句式特征
    sentence_length_preference: Literal["short", "medium", "long", "mixed"] = "mixed"
    common_openers: list[str] = Field(default_factory=list)  # 口头禅/常用开头
    common_closers: list[str] = Field(default_factory=list)
    
    # 情绪表达
    anger_expression: str = ""  # 如"短句+反问""沉默后爆发""
    fear_expression: str = ""
    joy_expression: str = ""
    sadness_expression: str = ""
    
    # 修辞习惯
    metaphor_frequency: Literal["rare", "moderate", "frequent"] = "moderate"
    irony_usage: bool = False
    rhetorical_question_habit: bool = False
    
    # 互动特征
    interrupt_frequency: Literal["rare", "moderate", "frequent"] = "moderate"
    pause_habit: str = ""  # 如"思考时停顿""紧张时结巴""
    
    # 背景影响
    education_level_hint: str = ""  # 如"文言词汇""粗俗用语""
    social_role_speech_pattern: str = ""  # 如"命令式""讨好式""平等式""
    
    generated_at: str = ""
```

## 生成 Prompt 示例

```markdown
请为角色 {character_name} 生成对话风格卡。

角色背景：{background}
性格特征：{personality_traits}
角色定位：{role_type}

要求：
1. 句式偏好应与性格一致（如急躁角色用短句）
2. 情绪表达应有具体模式（不是"生气时大声"而是"生气时冷笑+反问"）
3. 至少给出 2 个口头禅或常用开头
4. 风格应与角色的社会地位和成长背景相符

输出 JSON 格式，严格符合 DialogueStyleCard schema。
```

## Writer Prompt 注入格式

```markdown
## 出场角色对话风格

### {character_name}（{role_type}）
- 口头禅：{common_openers}
- 句式：{sentence_length_preference}
- 愤怒时：{anger_expression}
- 紧张时：{pause_habit}
- 修辞习惯：{metaphor_frequency} 隐喻，{irony_usage} 反讽
```

## 测试要求

- [ ] `DialogueStyleCard` 模型能正确序列化/反序列化
- [ ] CreativeDirector 能为 3 个角色生成风格卡
- [ ] Writer Prompt 包含风格卡后，对话审查的 distinctness 评分提升
- [ ] DB 能正确写入/读取风格卡
- [ ] 风格卡为空时不影响 Writer 正常运行

## 验收标准

- [ ] `pytest tests/ -x -q` 全部通过
- [ ] 至少 3 个角色的风格卡在集成测试中验证
- [ ] Writer 生成文本在模拟审查中 dialogue_distinctness 评分 >= 6.0
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/074-dialogue-quality-specialist-DONE.md`

## 参考文档

- `src/songyan/agents/creative_director/__init__.py` — CreativeDirector
- `src/songyan/agents/writer.py` — Writer
- `src/songyan/models/character.py` — `Character` 模型
- `prd/v3.0-058b-review-and-recommendations.md` — 6.3 节对话质量分析

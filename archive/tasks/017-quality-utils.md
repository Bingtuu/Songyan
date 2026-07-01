# Task 017: Quality Utils — 质量检测工具模块

## Goal
实现 5 个纯代码质量检测工具，为 RuleAuditor 提供底层检测能力。

## Read
- CLAUDE.md（约束清单）
- docs/INDEX.md
- src/songyan/models/review.py（AiTellMatch, FatigueWordMatch, RuleAuditResult）
- src/songyan/models/settlement.py（NumericalUpdate, Increment, Decrement）
- src/songyan/models/genre.py（GenreProfile.fatigue_words）
- genres/xuanhuan.json（疲劳词参考）

## In Scope

### 1. utils/ai_tells.py — AI 腔检测
- `AI_TELL_PATTERNS`: 正则模式列表（中文 AI 写作常见痕迹）
- `detect_ai_tells(text: str) -> list[AiTellMatch]`
- 定位信息格式：`"第{段}段第{句}句"`
- 目标：< 50ms

### 2. utils/fatigue_words.py — 疲劳词检测
- `detect_fatigue_words(text: str, fatigue_words: list[str]) -> list[FatigueWordMatch]`
- 支持多字短语匹配（如"嘴角勾起一抹弧度"）
- 统计出现次数和每个出现位置
- 目标：< 20ms

### 3. utils/hook_checker.py — 钩子检测
- `check_opening_hook(text: str) -> bool` — 前 300 字是否有吸引力事件
- `check_ending_hook(text: str) -> bool` — 最后 200 字是否有有效悬念
- 启发式规则：人称代词、动作动词、对话、冲突词、转折词等
- 目标：< 10ms

### 4. utils/paragraph_rhythm.py — 段落节奏分析
- `RhythmScore` Pydantic 模型（平均长度、单句比例、超长比例、对话比例、得分、问题列表）
- `analyze_paragraph_rhythm(text: str) -> RhythmScore`
- 评分逻辑：平均段长 80-150 字为最佳，单句段 <15%，超长段 <10%，对话段 20-40%
- 目标：< 30ms

### 5. utils/numerical_validator.py — 数值公式验证
- `NumericalContext` Pydantic 模型
- `validate_numerical_update(update: NumericalUpdate) -> list[str]`
- 验证 `closing_value == opening_value + sum(increments) - sum(decrements)`
- 返回空列表表示验证通过，非空列表为错误描述

### 6. 辅助函数
- `_locate_position(text: str, start: int, end: int) -> str` — 计算 `"第{段}段第{句}句"`
- 按中文标点断句（。！？…）
- 按换行分段

## Out of Scope
- RuleAuditor 的调用逻辑（Task 012）
- Writer 中的预防
- Token 计数器（Task 010 ContextManager）

## Acceptance Criteria
- [ ] AI 腔检测能识别至少 10 种常见模式（< 50ms）
- [ ] 疲劳词检测能统计短语出现次数（< 20ms）
- [ ] 首屏钩子检测正确判断前 300 字（< 10ms）
- [ ] 章末钩子检测正确判断最后 200 字（< 10ms）
- [ ] 段落节奏分析输出 0-10 分（< 30ms）
- [ ] 数值公式验证正确计算 opening + increments - decrements == closing
- [ ] **所有检测总耗时 < 200ms**（集成测试）
- [ ] 每个模块有独立测试文件，覆盖正常/边界/异常场景
- [ ] 所有函数带类型标注
- [ ] 单文件不超过 400 行
- [ ] ruff 0 errors
- [ ] pytest 全通过

## Dependencies
- Phase 1 全部完成

## Notes
- 纯代码工具，不调用 LLM
- 测试不依赖外部 API
- 定位信息使用中文格式（第X段第Y句）

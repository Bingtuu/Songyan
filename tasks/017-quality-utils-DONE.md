# Task 017: Quality Utils — 交接报告

## 做了什么

实现 5 个纯代码质量检测工具模块，为 RuleAuditor（Task 012）提供底层检测能力。

## 改动的文件

### 新增源码
- `src/songyan/utils/__init__.py` — 公共 API 导出
- `src/songyan/utils/_helpers.py` — 共享辅助函数（分段、断句、定位）
- `src/songyan/utils/ai_tells.py` — AI 腔检测（18 种正则模式）
- `src/songyan/utils/fatigue_words.py` — 疲劳词检测（短语匹配 + 位置统计）
- `src/songyan/utils/hook_checker.py` — 首屏/章末钩子检测（启发式规则）
- `src/songyan/utils/paragraph_rhythm.py` — 段落节奏分析（RhythmScore 模型 + 0-10 评分）
- `src/songyan/utils/numerical_validator.py` — 数值公式验证（玄幻专用，验证 closing == opening + inc - dec）

### 新增测试
- `tests/utils/__init__.py`
- `tests/utils/test_ai_tells.py` — 12 个测试（含 16 个已知短语覆盖）
- `tests/utils/test_fatigue_words.py` — 10 个测试（含 xuanhuan 集成测试）
- `tests/utils/test_hook_checker.py` — 16 个测试
- `tests/utils/test_paragraph_rhythm.py` — 8 个测试
- `tests/utils/test_numerical_validator.py` — 14 个测试

### 新增 Task 文件
- `tasks/017-quality-utils.md` — Task 规格

## 如何运行

```bash
# 运行 utils 测试
pytest tests/utils/ -v

# 运行全部测试
pytest -v

# 代码风格检查
ruff check src/songyan/utils/ tests/utils/
```

## 验证结果

- `pytest tests/utils/`：**77 passed, 0 failed**
- `pytest`（全量）：**279 passed, 0 failed**（202 原有 + 77 新增）
- `ruff check`：**0 errors**

## 已知限制

1. **AI 腔检测**：基于正则模式匹配，可能漏检新型 AI 写作痕迹。模式集可扩展。
2. **首屏钩子检测**：启发式规则较简单，无法判断"好的环境描写开头"与"无聊的环境描写开头"的区别。
3. **段落节奏评分**：基于固定阈值（80-150 字/段），不同题材可能有不同的最优范围。
4. **性能**：AI 腔检测在大文本上约 100ms， fatigue 词检测约 50ms，均满足 < 200ms 总耗时要求，但还有优化空间（如预编译正则、Aho-Corasick 字符串匹配）。

## 还没做什么

- Token 计数器（将在 Task 010 ContextManager 中实现）
- RuleAuditor 的调用集成（Task 012）
- Craft Card Prompts（Task 018）

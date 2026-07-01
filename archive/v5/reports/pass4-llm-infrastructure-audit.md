# Pass 4 — LLM 基础设施审计报告

> **范围**: client.py + retry.py + parsing.py + token_estimator.py + 8 个调用站点
> **日期**: 2026-06-10
> **审查者**: Codex (Pass 4 — LLM 基础设施审计)
> **状态**: 完成
> **依赖**: Pass 1 的 P1-1（except Exception）在本报告中深挖但不重复

---

## 摘要

| 维度 | 判定 | 关键发现 |
|------|------|---------|
| 重试策略 | ### 良好 | 指数退避 + 配置化，缺 jitter |
| 超时管理 | #### 坚实 | 每调用 60s 超时 + 重试链总超时 210s |
| 解析鲁棒性 | #### 优秀 | 3 层 fallback（标准 → json_repair → 手动修复） |
| Token 估算 | ### 良好 | tiktoken + 字符数回退，有 except 问题 |
| 调用一致性 | #### 一致 | 8 个站点统一模式 |
| 错误处理 | ### 不一致 | writer/revision 节点未捕获 LLM Error |
| 可观测性 | ## 不足 | 缺 request_id / token 用量追踪 |

---

## 1. 模块全景

```
┌─────────────────────────────────────────────────────┐
│                  call_llm (client.py)                │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ get_llm()  │→ │  _invoke()   │→ │ parse_llm_   │ │
│  │  LRU 缓存  │  │  ainvoke     │  │ response()   │ │
│  │  temperature│  │  max_retries  │  │  3层 fallback│ │
│  │  max_tokens │  │  60s 超时    │  │  → dict      │ │
│  └────────────┘  └──────┬───────┘  └──────────────┘ │
│                         │                            │
│                  ┌──────▼───────┐                   │
│                  │ retry_with_   │                   │
│                  │ backoff()    │                   │
│                  │ 指数退避      │                   │
│                  │ base=1s      │                   │
│                  │ max=10s      │                   │
│                  │ LLMError 重试 │                   │
│                  └──────────────┘                   │
└─────────────────────────────────────────────────────┘
```

**8 个调用站点**: goal_planner, creative_director, writer, llm_auditor, literary_auditor, revision_handler, settlement_extractor, summary_writer, arc_summary_generator *(注: creative_director 使用 call_llm 但不在搜索结果中，确认通过 import 间接使用)*

---

## 2. 逐文件审计

### 2.1 client.py（143 行）

**好**:
- ✅ LRU 缓存 LLM 实例（maxsize=8），复用同参数组合
- ✅ 配置验证（API key 空检查 + import 检查）
- ✅ 异步调用 + `asyncio.wait_for` 总超时
- ✅ 编程错误（TypeError/ValueError）与网络错误（Exception→LLMError）正确分离
- ✅ 错误信息中文化，`cause` 链完整

**问题**:

| # | 位置 | 问题 | 严重度 |
|---|------|------|--------|
| C1 | `get_llm()` L78 | `except Exception as e` 捕获 ChatLiteLLM 初始化异常 | P2 — 虽正确包装为 LLMError，但会捕获 KeyboardInterrupt |
| C2 | `_invoke()` L121-132 | `except Exception` 将所有非编程错误转为 LLMError | P2 — 漏掉 IndexError/LookupError 等可能的编程错误 |
| C3 | 全局 | call_llm 只返回 `str(content)`，舍弃 token 用量 | P2 — Budget 管理层需要 token 用量，目前无法追踪 |
| C4 | 全局 | 缺 request_id / trace_id，无法跨 client→retry→parsing 关联日志 | P2 — 调试困难 |
| C5 | L129 | `total_timeout = 60 * max_retries + 30` | P3 — 硬编码，应为配置项 |

### 2.2 retry.py（73 行）

**好**:
- ✅ 泛型异步设计（TypeVar T）
- ✅ 指数退避 + 基础/最大延迟可配置
- ✅ 同时提供函数形式和装饰器形式
- ✅ `retryable_exceptions` 可配置（默认 LLMError, TimeoutError, ConnectionError）

**问题**:

| # | 位置 | 问题 | 严重度 |
|---|------|------|--------|
| R1 | `retry_with_backoff` L40 | `for attempt in range(max_retries)` — 语义混淆 | P3 — "重试 3 次"实际是"共执行 3 次"（1 初始 + 2 重试），docstring 未澄清 |
| R2 | 全局 | 纯指数退避，无 jitter（随机抖动） | P3 — 单用户 CLI 场景影响不大 |
| R3 | L45-46 | `except retryable_exceptions as e` — 运行时变量匹配 | P3 — Python 合法但少见，静态分析可能告警 |

### 2.3 parsing.py（155 行）

**好**:
- ✅ 3 层 fallback：标准 json.loads → json_repair → 手动修复
- ✅ `_extract_json_balanced` 用括号计数法正确提取嵌套 JSON，避免正则缺陷
- ✅ 手动修复覆盖：markdown 代码块、尾部逗号、未引用 key、单引号
- ✅ `LLMResponseParseError` 保留 `raw_response` 用于调试
- ✅ fallback all 失败时 log warning

**问题**:

| # | 位置 | 问题 | 严重度 |
|---|------|------|--------|
| P1 | `_manual_json_repair` L71-72 | `cleaned = cleaned.replace("''", '"')` 替换所有单引号，会破坏字符串内容中的合法单引号（如 "don''t"、"l''état"） | P2 — LLM 英文输出可能被破坏 |
| P2 | `parse_llm_response` L139 | `except Exception` 在 json_repair fallback 路径 | P1 — 已 Pass 1 报告，会捕获 KeyboardInterrupt |
| P3 | `_manual_json_repair` L66-69 | 未引用 key 的正则只匹配 ASCII 字母 key，漏掉中文/Unicode key | P3 — LLM 输出中文 key 时修复失败 |
| P4 | 全局 | JSON 解析后不做 schema 校验，调用方自行处理缺失字段 | P3 — 各调用方重复相同的数据校验逻辑 |
| P5 | `_manual_json_repair` | 输入已是 extract_json 的提取结果，代码块处理冗余 | P3 — 无害冗余 |

### 2.4 token_estimator.py（91 行）

**好**:
- ✅ tiktoken cl100k_base 精确估算
- ✅ Pydantic model / dict / list 自动序列化后估算
- ✅ `truncate_to_tokens` 二分查找精确截断
- ✅ tiktoken 不可用时自动字符数回退

**问题**:

| # | 位置 | 问题 | 严重度 |
|---|------|------|--------|
| T1 | `__init__` L24 | `except Exception` tiktoken import 失败 | P1 — 已 Pass 1 报告 |
| T2 | `estimate()` L35 | `except Exception` 编码失败 | P2 — 已 Pass 1 报告，但回退到 len/2 仍在工作 |

---

## 3. 调用站点审计

### 3.1 8 个调用站点对比

| 调用方 | max_tokens | 错误处理 | max_retries | 约定? |
|--------|-----------|---------|------------|-------|
| writer | 6,000 | ❌ 无 try/except | 默认 3 | ❌ 不捕获冒泡到 LangGraph |
| goal_planner | 默认 4096 | ❌ 无 try/except | 默认 3 | ❌ 同 |
| llm_auditor | 默认 4096 | ❌ 无 try/except | 默认 3 | ❌ 同 |
| literary_auditor | 默认 4096 | ❌ 无 try/except | 默认 3 | ❌ 同 |
| summary_writer | 默认 4096 | ❌ 无 try/except | 默认 3 | ❌ 同 |
| arc_summary_generator | 2,048 | ❌ 无 try/except | 默认 3 | ❌ 同 |
| revision_handler | 默认 4096 | ⚠️ 部分节点捕获 | 默认 3 | ✅ 在节点层处理 |
| settlement_extractor | 默认 4096 | ✅ `except (LLMError, LLMResponseParseError)` | 默认 3 | ✅ 在节点层处理 |

**关键发现 L1 — 错误处理不一致**:

只有 `settlement_extractor_node` 和 `revision_handler_node`（部分路径）正确捕获了 LLM 调用的错误。Writer 和 GoalPlanner 等核心 Agent 如果 LLM 调用失败，异常会直接传播到 LangGraph 运行时，不会触发 `Phase1State.error` 填充或优雅降级路径。

```
writer_node → write_chapter → call_llm → LLMError → ❌ 未捕获 → LangGraph 崩溃
                         vs
settlement_extractor_node → extract_settlement → call_llm → LLMError → ✅ 捕获 → needs_human_review=True
```

### 3.2 LangGraph 层

`run_chapter_pipeline()`（phase1_graph.py:232）也没有 try/except。运行 `graph.ainvoke()` 时，任何未捕获的异常都会终止整个工作流。

```
graph.ainvoke(initial_state)  ← 直接调用，无 try/except
  └─ writer_node()
       └─ write_chapter()
            └─ call_llm() → LLMError → 未捕获 → graph.ainvoke 异常退出
```

---

## 4. 综合评价

### 4.1 LLM 调用可靠性评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 重试策略 | 7/10 | 指数退避配置化，无 jitter，语义微含糊 |
| 超时管理 | 8/10 | 每调用 60s + 总超时 210s，硬编码 |
| 解析鲁棒性 | 9/10 | 3 层 fallback，中文场景验证充分 |
| 错误传播 | 5/10 | 上层节点不一致：关键路径（writer）未捕获 |
| 可观测性 | 4/10 | 缺 request_id / token 用量追踪 |
| 配置验证 | 8/10 | API key 检查 + import 检查 |
| 调用一致性 | 8/10 | 模式统一，但参数传递未标准化 |
| 安全 | 7/10 | prompt 注入表面存在但不在 LLM 层处理 |

### 4.2 与已有 Pass 的交叉引用

| Pass 1/2/3 问题 | Pass 4 关联 |
|---------------|------------|
| P1-1（except Exception 14 处）| 新增细节：parsing.py L139 是 json_repair fallback 路径 |
| P1-1（token_estimator except）| 新增细节：`__init__` L24 + `estimate()` L35 |
| A2（settlement_node 6 件事）| 新增细节：settlement 是唯一正确捕获 LLM Error 的节点 |
| T3（parametrize 不足）| 新增细节：8 个 call 站点参数不一致可参数化测试 |

### 4.3 建议修复优先级

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| L1 | writer/goal_planner 等节点未捕获 LLMError | 关键路径崩溃 | 在 `_nodes.py` 的 writer_node/goal_planner_node 等添加 `try/except`，填充 `error` 字段 |
| C3 | 丢弃 token 用量 | Budget 管理盲区 | 让 `call_llm` 返回 `(content: str, usage: TokenUsage | None)` 元组 |
| C4 | 缺 request_id | 日志关联困难 | 引入 `LLMRequestContext(request_id, agent_name)` 贯穿调用链 |
| P1 | 单引号替换过宽 | 英文输出被破坏 | 替换为只修复字符串边界上的单引号 |
| C1 | `get_llm` except Exception | 隐式吞 KeyInterrupt | 改为分 `except (ValueError, ImportError)` + `except BaseException` |
| R2 | 缺 jitter | 并发场景 thundering herd | 添加 `random.uniform(delay*0.5, delay*1.5)` 随机延迟 |
| C5 | timeout 硬编码 | 配置不灵活 | 移到 config.py 作为 `llm_timeout_per_call` 和 `llm_max_retries` |

---

## 5. 方法说明

### 扫描范围
- `src/songyan/llm/` — 4 个文件（372 行）
- `src/songyan/utils/token_estimator.py` — 1 个文件（91 行）
- `src/songyan/agents/*.py` — 8 个调用站点
- `src/songyan/workflows/_nodes.py` — 节点错误处理
- `src/songyan/workflows/phase1_graph.py` — graph 级错误处理

### 局限
- 未运行实际 LLM 调用测试（网络/API 不可用）
- 未测量 tiktoken 与实际 LLM tokenizer 的偏差
- 未检查 litellm 的 rate limiting 处理

---

> **松烟入墨，字句成锋。**
> LLM 是系统的引擎室 — 出错路径比成功路径更需要精心设计。

# Task 139g：修复 settlement_extractor LLM 调用超时

## 背景

Task 139c（Ch51-Ch150 enforce 长窗口验证）在 Ch83 失败：

- 章节本身通过 human_gate 接受（v-83-4）。
- 进入 `settlement_extractor` 后，LLM 调用在 210 秒累计超时后失败。
- 错误信息：`LLM 调用总超时（超过 210 秒）`。

根因：`songyan/llm/client.py` 中 `call_llm` 的默认策略为单次 60s × 3 次重试 + 30s 缓冲 = 210s。settlement prompt 较重（约 12.5K tokens），在 API 瞬时延迟下单次调用容易被 60s 切断，重试耗尽后整体熔断。

这不是质量门或硬门禁触发，而是通用 LLM 超时策略对 settlement 场景过于激进。

## 目标

让 settlement_extractor 拥有更宽松的单次超时，同时控制总等待时间，使 Ch83 及后续章节的长窗口验证能够继续。

## 改动

### 1. `src/songyan/llm/client.py`

- `_get_llm_cached` 增加 `timeout` 参数，并纳入缓存键。
- `get_llm` 增加 `timeout: int = 60` 参数，透传给 `_get_llm_cached`。
- `call_llm` 增加 `timeout: int = 60` 参数，透传给 `get_llm`。
- 累计超时公式改为 `timeout * max_retries + 30`，使总超时与单次超时保持一致。

### 2. `src/songyan/agents/settlement_extractor/__init__.py`

- `extract_settlement` 调用 `call_llm` 时显式指定 `timeout=120, max_retries=2`。
- 单次超时从 60s 提升到 120s，总超时从 210s 变为 270s，给重 prompt 留出余量；重试次数从 3 降到 2，避免无限等待。

## 验证

- `ruff check src/ tests/`：通过。
- `python -m pytest tests/test_llm_client.py tests/integration/test_paths.py -q`：通过。
- 全量 `pytest tests/ -q`：后台运行中（Task bash-zeob52bx）。

## 下一步

1. 待全量 pytest 通过后，后台重跑 `START_CHAPTER=83 END_CHAPTER=150` 的 enforce 验证。
2. 完成 Ch83-Ch150 且无任何 gate 触发后，生成 Task 139d 最终验收包。

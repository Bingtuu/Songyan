# Pass 8: 测试质量与覆盖审计报告

## 执行摘要
- **发现总数**: 4
- **P0**: 0, **P1**: 0, **P2**: 4
- **关键结论**: 全量测试 `2397 passed, 2 skipped, 1 xfailed, 2 warnings` 通过；V7 新子系统测试均 green；集成/E2E 测试覆盖 accept/edit/reject/back、断点续跑、AutoHalt 等主路径；主要短板是部分测试未复用 `conftest.mock_llm` 统一 fixture、个别超长测试未标记 `performance`、部分内部工具模块缺少独立单测。

## 检查项与发现

### 8-1 部分测试未复用统一 `mock_llm` fixture
- **级别**: P2
- **文件**: 多个测试文件（如 `tests/test_writer.py`, `tests/test_revision_handler.py`, `tests/test_llm_auditor.py`, `tests/integration/test_ch1_20_e2e.py` 等）
- **问题描述**: `tests/conftest.py` 已提供统一的 `mock_llm` fixture，用于 patch `songyan.llm.client.call_llm`。但大量测试仍自行使用 `with patch("songyan.agents.xxx.call_llm", ...)` 或 `patch("songyan.agents.writer.call_llm")` 等方式 mock。这导致 mock 目标分散，若 LLM 调用链路重构（如统一改为 patch `get_llm`），维护成本较高。
- **证据**:
  ```python
  # tests/conftest.py:30-35
  @pytest.fixture
  def mock_llm():
      with patch("songyan.llm.client.call_llm") as mock:
          mock.return_value = '{"result": "test"}'
          yield mock
  ```
  全局搜索 `patch("songyan.agents.` 得到约 50+ 处分散 mock。
- **潜在影响**: 新增或重构 Agent 时容易遗漏 mock 点；测试与实现耦合度偏高。
- **修复建议**: 对纯 `call_llm` mock 场景，优先使用 `mock_llm` fixture；对需要自定义返回值的测试，通过 `mock_llm.return_value = ...` 覆盖。E2E/集成测试中多 Agent 联调可保留局部 mock。
- **验证方式**: `rg 'patch\("songyan\.agents\..*\.call_llm"' tests/ -c` 计数下降。

### 8-2 超长测试未全部标记 `performance`
- **级别**: P2
- **文件**: `tests/integration/test_122d_long_sequence_stability.py`, `tests/integration/test_ch41_50_validation.py`, `tests/integration/test_ch1_20_e2e.py`
- **问题描述**: 全量测试运行约 520 秒（8 分 40 秒），前 3 个最慢测试均超过 20 秒，其中 `test_accepted_chapter_skip` 接近 48 秒。虽然这些测试天然属于集成/E2E 范畴，但未使用 `pytest.mark.performance` 标记，无法在快速反馈循环中通过 `-m "not performance"` 跳过。
- **证据**（慢测试前 10）：
  | 用时 | 测试 |
  |------|------|
  | 47.97s | `tests/integration/test_122d_long_sequence_stability.py::test_accepted_chapter_skip` |
  | 25.10s | `tests/integration/test_ch41_50_validation.py::test_ch41_50_long_chain_validation` |
  | 23.73s | `tests/integration/test_ch1_20_e2e.py::test_ch1_20_e2e_validation` |
  | 12.54s | `tests/integration/test_paths.py::test_path_b_one_round_revision_accept` |
  | 10.35s | `tests/integration/test_122d_long_sequence_stability.py::test_context_budget_150_chapters` |
  | 9.97s  | `tests/test_settlement_extractor.py::TestConcurrentSettlement::test_concurrent_settlement_writes` |
  | 9.11s  | `tests/test_151_mr_adaptive_cap_and_relevance.py::TestAssemblyIntegration::test_assembly_passes_inputs` |
  | 8.53s  | `tests/test_dialogue_style_card.py::TestCreativeDirectorDialogueStyle::test_generate_for_characters_without_cards` |
  | 8.25s  | `tests/test_eval_runner.py::test_run_seed_project_all_configs` |
  | 6.76s  | `tests/integration/test_paths.py::test_path_i_revision_rebound_rollback` |
- **潜在影响**: 本地/CI 快速检查无法过滤重测试；开发迭代反馈慢。
- **修复建议**: 对 >10s 的集成/E2E/稳定性测试添加 `@pytest.mark.performance`，并将 `pytest.ini`/`pyproject.toml` 默认 deselect performance 的选项文档化（当前已配置 `markers`，但未默认排除）。
- **验证方式**: `pytest tests/ -m "not performance" -q` 运行时间应显著低于全量（目标 <120s）。

### 8-3 部分内部工具模块缺少独立测试
- **级别**: P2
- **文件**: `src/songyan/agents/settlement_extractor/_apply.py`, `_validate.py`, `_constraints.py`, `_quote_filter.py`, `_scanners.py` 等
- **问题描述**: 核心 Agent（Writer、RevisionHandler、SettlementExtractor、Auditor）均有较完整测试，但部分内部辅助模块（如结算应用器、验证器、约束过滤器、引用过滤器、扫描器）缺乏独立单元测试，依赖集成测试间接覆盖。一旦内部实现细节变更，问题可能在集成测试才暴露。
- **证据**: 搜索 `tests/test_*apply*.py`、`tests/test_*validate*.py`、`tests/test_*scanner*.py` 等无对应独立测试文件；`test_settlement_extractor.py` 虽然覆盖广，但主要通过 SettlementExtractor 公共接口间接覆盖内部 `_apply`/`_validate`。
- **潜在影响**: 内部重构缺少快速反馈；边界条件（如 `character_update.old_value` 校验、`new_setting.source_quote` 正文存在性校验）的独立验证不足。
- **修复建议**: 为 `_validate.py` 中的校验函数、`_apply.py` 中的原子操作、`_constraints.py` 中的过滤规则增加独立单元测试，尤其在结算证据门禁（Task 138f）相关路径上。
- **验证方式**: 新增 `tests/settlement_extractor/test_apply.py`、`test_validate.py` 等，并确保 `pytest tests/settlement_extractor/ -q` 全部通过。

### 8-4 E2E 测试对 RAG Embedder 懒加载触发较深
- **级别**: P2
- **文件**: `tests/test_151_mr_adaptive_cap_and_relevance.py`, `tests/test_dialogue_style_card.py`, `tests/test_eval_runner.py`
- **问题描述**: 多个非 performance 标记的测试耗时 5-10 秒，主要原因是首次触发 `sentence-transformers` 模型加载/分词器初始化。这表明 RAG Embedder 的懒加载在测试中反复发生，且无全局 fixture 预加载或缓存共享。
- **证据**: `test_151_mr_adaptive_cap_and_relevance.py::TestAssemblyIntegration::test_assembly_passes_inputs`（9.11s）、`test_dialogue_style_card.py::...test_generate_for_characters_without_cards`（8.53s）、`test_eval_runner.py` 多个测试 2-8s。
- **潜在影响**: 单元测试层不应承担模型加载开销；测试运行时间被拉长，且结果受本地模型缓存影响。
- **修复建议**: 在 `conftest.py` 中提供 `mock_embedder` fixture，对非 Embedder 专项测试默认 mock 向量模型；Embedder 本身测试保留真实/缓存加载。
- **验证方式**: `pytest tests/ -m "not performance" --durations=10 -q` 前 10 慢测试平均耗时下降。

## 通过项

| 检查项 | 结论 | 证据 |
|--------|------|------|
| 全量测试通过 | 通过 | `pytest tests/ --durations=20 -q` 结果：`2397 passed, 2 skipped, 1 xfailed, 2 warnings` |
| V7 新子系统测试 | 通过 | Task 166/167/168/169 相关测试（`test_166*.py`, `test_167*.py`, `test_168*.py`, `test_169*.py`）均包含在全量结果中，无失败 |
| 测试数据库隔离 | 通过 | `tests/conftest.py` 提供 `test_db` fixture，为每个测试创建独立 `tmp_path/test.db`；`checkpointer_mode` 切为 `memory` |
| 统一 mock fixture 存在 | 通过 | `tests/conftest.py:30` 提供 `mock_llm`，patch `songyan.llm.client.call_llm` |
| E2E 覆盖主要路径 | 通过 | `tests/integration/test_paths.py` 覆盖 one-round revision、two-rounds forced pass、revision rebound rollback；`test_ch1_20_e2e.py` / `test_ch41_50_validation.py` / `test_122d_long_sequence_stability.py` 覆盖长链、断点续跑、预算稳定性 |
| 参数化边界覆盖 | 通过 | `test_settlement_extractor.py` 大量使用 `@pytest.mark.parametrize` 覆盖空值、重复、并发、数值校验等边界；`tests/creative_modes/test_registry.py`、`tests/genres/` 参数化多个 genre/mode |
| xfailed 已知项 | 通过 | 仅 1 个 xfailed，文档说明为已知非阻断项；0 xpassed |
| 测试卫生 | 通过 | 未发现明显 skip/xfail 滥用；`tests/evals`、`tests/cli` 按 `pyproject.toml` 默认忽略 |

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 8-1 | P2 | 分散 mock 未复用 `mock_llm` | 各测试文件 | `rg 'patch\("songyan\.agents\..*\.call_llm"' tests/ -c` |
| 8-2 | P2 | 慢测试未标记 performance | 集成/E2E 测试 + `pyproject.toml` | `pytest tests/ -m "not performance" -q` |
| 8-3 | P2 | 内部工具模块缺独立测试 | `tests/settlement_extractor/`, `tests/agents/` 等 | `pytest tests/ -q` |
| 8-4 | P2 | Embedder 懒加载拖累单元测试 | `tests/conftest.py` + 相关测试 | `pytest tests/ -m "not performance" --durations=10 -q` |

---
> 审计结论：测试基线健康，无 P0/P1 风险；P2 项集中在测试工程效率与边界覆盖补强，不阻塞 Ch200 爬坡，但建议在 Task 170 前落地以提升迭代速度。

# Pass 16: 测试 suite 与工程质量审计报告

> **审计日期**: 2026-07-13
> **项目基线**: V7 Task 171w 完成后
> **全量测试**: `2623 passed, 2 skipped, 1 xfailed, 2 warnings in 423.32s`
> **审查范围**: `pyproject.toml`, `tests/conftest.py`, 171/170/16x 系列测试, 核心测试, `tests/integration/`, 全量 pytest 慢测试, ruff, mypy

---

## 执行摘要

功能测试覆盖较好且全部通过，ruff 干净。**但 mypy 在 strict 模式下未通过（>100 条错误）、全量 suite 超过 7 分钟、部分测试目录被排除在 pytest 外、CRLF 污染较广。** 这些问题不直接阻塞 Ch250 长跑，但会显著降低工程效率和类型安全性。

| 级别 | 数量 | 关键问题 |
|---|---|---|
| P0 | 2 | mypy strict 失败；全量 pytest 超过 7 分钟 |
| P1 | 5 | evals/cli 被忽略、mock 未统一、CRLF 污染、真实类型混用 |
| P2 | 6 | 慢测试未标记、覆盖度低、fixture 缺失、弃用警告 |

---

## P0 级问题

### P0-1 `mypy src/` 在 strict 模式下失败

- **文件**: `src/songyan/` 多处
- **典型错误**:
  - `src/songyan/workflows/review_merger.py:389,398,412` — 把 `AiTellMatch`/`FatigueWordMatch` 赋值给声明为 `DuplicateParagraphMatch` 的变量
  - `src/songyan/agents/rule_auditor.py:538` — 反向类型不匹配
  - `src/songyan/agents/writer.py:396-400` — 把 `SoftReference` 对象当 `dict` 使用
  - `src/songyan/db/repository.py:309,576` 等类型推断错误
- **问题描述**: `pyproject.toml` 声明 `strict = true`，但实际 `mypy src/` 输出超过 100 条 error。部分错误指向真实运行时类型混用风险。
- **潜在影响**: CI/本地实际无法通过类型检查；类型错误中部分指向真实运行时类型混用风险。
- **修复建议**:
  1. 优先修复“真实类型不匹配”类错误（review_merger、rule_auditor、writer）。
  2. 对大量 `Missing type arguments for generic type "dict"` 统一补全泛型参数。
  3. 缺失 stub（yaml、transformers 等）通过 `types-PyYAML` 或 `ignore_missing_imports` 处理。
  4. 在 `src/` 根添加 `py.typed`，并考虑 CI 中增加 `mypy src/` 门禁。

### P0-2 全量 `pytest tests/` 超过合理/CI 可接受时间

- **文件**: `pyproject.toml:57-63`
- **证据**:
  - 全量 `pytest tests/` 完成 2623 passed，耗时 **423.32s（约 7 分 3 秒）**。
  - 分项：非 integration 全量约 270s；integration 约 180s。
- **潜在影响**: CI 容易因超时失败；本地反馈慢，降低开发者运行全量 suite 的意愿。
- **修复建议**:
  1. 将 `tests/integration/test_ch1_20_e2e.py`、`test_ch41_50_validation.py`、`test_122d_long_sequence_stability.py` 等超过 10s 的 E2E 用例标记为 `@pytest.mark.performance`。
  2. 默认 CI 跑 `pytest -m "not performance"`；单独 job 跑完整 performance/integration。
  3. 为长测试配置 `--timeout=120` 等硬超时，避免 hung 住。

---

## P1 级问题

### P1-1 `tests/evals` 与 `tests/cli` 被 pytest 整体忽略

- **文件**: `pyproject.toml:59`
- **代码**: `addopts = "--ignore=tests/evals --ignore=tests/cli"`
- **问题描述**: 目录下仍存在测试文件，但被全局忽略。
- **潜在影响**: evals 与 CLI 代码改动无自动化回归保护。
- **修复建议**: 明确是否故意排除；若不是，移除 `--ignore` 并在 CI 单独运行；若是，在文档/AGENTS.md 中说明原因。

### P1-2 mock LLM 仍未统一

- **文件**: `tests/conftest.py:30`, `tests/integration/conftest.py:64`
- **问题描述**: 根 `conftest.py` 的 `mock_llm` 仅 patch `songyan.llm.client.call_llm`；integration 套件拥有独立的 sequenced mock；171/170/16x 系列测试大多在测试内部直接 `patch("songyan.agents.xxx.call_llm", ...)`。
- **潜在影响**: 多处重复维护 mock target 列表；`mock_llm` fixture 形同虚设。
- **修复建议**: 把 `mock_call_llm` 的机制上提到根 `tests/conftest.py`，统一 patch 所有 agent 的 `call_llm`；逐步迁移现有测试使用统一 fixture。

### P1-3 多个文件存在 CRLF 行尾污染

- **文件**: `pyproject.toml`, `tests/conftest.py`, `tests/test_170j_experiment_harness.py`, `tests/test_revision_handler.py`, `tests/test_phase1_graph.py`, `tests/test_phase2_graph.py`, `tests/integration/conftest.py`, `tests/integration/test_ch41_50_validation.py`, `tests/integration/test_checkpoint.py`, `tests/integration/test_multi_chapter.py`, `tests/integration/test_paths.py`
- **问题描述**: 二进制扫描显示这些文件包含 `\r\n`。
- **潜在影响**: 跨平台 diff 噪音、Git 自动转换风险、偶尔导致工具/脚本解析异常。
- **修复建议**: 统一转换为 LF；添加 `.gitattributes` 强制文本文件 LF；CI 中增加 `git diff --check` 或 `file` 检查。

### P1-4 `review_merger` 与 `rule_auditor` 中疑似真实类型混用

- **文件**: `src/songyan/workflows/review_merger.py:389-428`, `src/songyan/agents/rule_auditor.py:538-541`
- **问题描述**: mypy 报错同一变量被赋值为不同类型的 match 对象。
- **潜在影响**: 运行时可能把 `AiTellMatch` 当 `DuplicateParagraphMatch` 处理，导致属性访问失败或错误生成 issue。
- **修复建议**: 审查这些循环/列表推导，确保变量类型一致；必要时拆分循环或使用 `Union` / `Any` 并加注释。

### P1-5 测试与脚本缺少类型注解（加剧 mypy 噪声）

- **文件**: `tests/test_170_adaptive_gate_validation.py`, `tests/test_171p_state_mismatch_construct.py`, `tests/test_162_timeline_consistency.py`, `tests/integration/conftest.py`, `scripts/run_158_ch1_ch100.py`, `scripts/run_170j_experiment.py` 等
- **问题描述**: mypy 报告函数缺少返回类型、泛型 dict 缺参数等。
- **修复建议**: 为核心测试 helper 添加类型；对脚本统一补全；或配置 `mypy` 仅对 `src/` 启用 strict、对 `tests/` 放宽。

---

## P2 级问题

### P2-1 慢测试未标记 `performance`

- **慢测试示例**:
  - `tests/integration/test_122d_long_sequence_stability.py::test_accepted_chapter_skip` — 23.39s
  - `tests/integration/test_ch41_50_validation.py::test_ch41_50_long_chain_validation` — 17.42s
  - `tests/integration/test_ch1_20_e2e.py::test_ch1_20_e2e_validation` — 14.16s
  - `tests/test_settlement_extractor.py::TestConcurrentSettlement::test_concurrent_settlement_writes` — 9.85s
- **修复建议**: 给上述 >5s 的 E2E/压力测试加 `@pytest.mark.performance`。

### P2-2 `test_170j_experiment_harness.py` 覆盖度过低

- **文件**: `tests/test_170j_experiment_harness.py`
- **问题**: 整文件仅 12 行，只测试了 `_resolve_db_path`。
- **修复建议**: 补充对实验配置解析、指标汇总、对比输出的最小测试。

### P2-3 `test_ch100_110_from_run_log.py` 在干净环境被跳过

- **文件**: `tests/integration/test_ch100_110_from_run_log.py:135,159`
- **问题**: 依赖 `run-a2bed648.jsonl` 和 `songyan.db`，新机器上默认跳过。
- **修复建议**: 将最小 fixture log 提交到 `tests/fixtures/`；或提供生成 fixture 的 setup 脚本。

### P2-4 `test_concurrent_settlement_writes` 被标记 xfail

- **文件**: `tests/test_settlement_extractor.py`
- **问题**: xfail reason 为 “SQLite on Windows does not guarantee concurrent writer progress across separate connections”。
- **修复建议**: 评估是否需要显式写队列/单 writer 线程；在文档中记录并发约束。

### P2-5 `transformers` WordPiece 弃用警告

- **文件**: `tests/test_151_mr_adaptive_cap_and_relevance.py`, `tests/integration/test_122d_long_sequence_stability.py`
- **问题**: `DeprecationWarning: WordPiece.__init__ will not create from files anymore...`
- **修复建议**: 升级 tokenizer 初始化方式，改用 `WordPiece.from_file`。

### P2-6 `pytest` 默认忽略 evals/cli 缺乏文档说明

- **问题**: 见 P1-1。
- **修复建议**: 在 `AGENTS.md` 或 `docs/INDEX.md` 中说明忽略原因。

---

## 正面发现

- 全量 2623 个测试通过，仅有 2 个跳过和 1 个预期失败（xfail）。
- ruff 检查完全通过，无新增告警。
- V7 新增测试（171 系列）覆盖了文学护栏、文本洁净、guardrail 持久化、文本 observe 等核心路径。
- Integration 测试覆盖了 E2E、断点续跑、长序列稳定性、多章运行等关键场景。

---

## 验证结果

```powershell
# 全量测试
python -m pytest tests/ -q
# 2623 passed, 2 skipped, 1 xfailed, 2 warnings in 423.32s

# ruff
ruff check src/ tests/
# All checks passed

# mypy
mypy src/
# >100 errors

# 慢测试
pytest tests/ --durations=30 -q
# 见上文
```

---

## 修复优先级

1. **P0-1**: 修复 mypy 真实类型错误并收敛 `mypy src/` 至 0 错误。
2. **P0-2**: 拆分慢测试，给 E2E/长链测试加 `@pytest.mark.performance`，使默认 `pytest` 在 3 分钟内完成。
3. **P1-1**: 决定是否把 `tests/evals`、`tests/cli` 纳入 pytest。
4. **P1-2**: 统一 mock LLM fixture。
5. **P1-3**: 清理 CRLF 行尾，添加 `.gitattributes`。
6. **P1-4 / P1-5**: 修复 review_merger/rule_auditor 类型混用；为测试 helper 补类型。
7. **P2**: 处理慢测试标记、覆盖度、弃用警告。

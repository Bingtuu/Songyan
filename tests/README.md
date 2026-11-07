# tests/

How the suite is laid out, and what must stay green while V1.0 assist work is planned. Product rules live in `AGENTS.md`. This file is only about tests.

## What CI runs

From `.github/workflows/ci.yml` and `pyproject.toml`:

```text
ruff check src/ tests/
python -m pytest tests/ -q
python -m pytest tests/cli -q
```

`[tool.pytest.ini_options] addopts` already ignores `tests/evals` and `tests/cli`. The CLI suite is the second pytest command, not the default one. `tests/evals` is research and is not a default release gate.

The `performance` marker does **not** skip tests. CI does not pass `-m "not performance"`. Those modules still have to stay green.

Ruff selects `E`, `F`, `I`, `N`, `W`, `UP` (`line-length` 100, target Python 3.11). Do not add a rule set that fails this command unless the owner asks.

## Layout

The tree is already partly packaged. Keep that. Do not reshuffle it into a new `tests/unit/` root.

| Path | Role |
|------|------|
| `tests/cli/` | Click surface. Ignored by default pytest; CI runs it on purpose. |
| `tests/db/` | SQLite schema, repos, plan-fact cards. |
| `tests/plan_checks/` | Thin-wrapper plan bible and the three narrow checks. Keep green. Do not add a new genre recall KPI here. |
| `tests/integration/` | Multi-chapter graph tests. Several are marked `performance` and still run in default pytest. |
| `tests/workflows/`, `tests/models/`, `tests/rag/`, `tests/genres/`, `tests/creative_modes/`, `tests/settlement_extractor/`, `tests/utils/` | Area tests for the current runtime. |
| `tests/literary_optimization/` | Strategy loader. Small, still collected. |
| `tests/evals/` | Research spikes (`test_196` … `test_206` and friends). Not in default pytest. |
| `tests/*.py` | Flat modules. Many are named after old task ids. They still protect runtime (import, settlement, gates, backup). They are not obsolete just because the filename has a number. |

Shared fixtures: `tests/conftest.py`. Integration helpers: `tests/integration/conftest.py`.

## Legacy names (keep, do not extend)

139 files match `test_<digits>`, `test_task###`, `test_v1#`, or a `task` plus digits anywhere in the name (`test_settlement_extractor_task134.py`). Examples: `test_242_settlement_savepoint_isolation.py` still guards settlement; `test_v14_llm_role_routing.py` still guards role routing. Number prefixes were reused (`test_158_*`, `test_173_*`, `test_175_*`, `test_185_*`, `test_171w_*` are different modules, not duplicates).

`tests/test_naming_policy.py` freezes that set. A new file with a legacy-style name fails the test. Deleting a legacy file means deleting its name from the allowlist in the same change. Do not add a name to admit a new test.

These five modules carry an explicit module docstring `LEGACY — taskNNN; keep green, do not extend`:

- `test_task135_continuity_governance.py`
- `test_task137_setting_recycling.py`
- `test_task138n_mandatory_reference_revision.py`
- `test_task138p_character_id_alias.py`
- `test_settlement_extractor_task134.py`

They were not moved to `tests/legacy/`. A mass move would still collect them, but it would churn imports and fixture scope for no gain. Nothing in this pass was deleted.

## Legacy semantics vs accepted M-docs（裁决规则）

旧 lineage 测试（`test_<数字>_*.py` 等，见上节）断言的是当年引擎语义。当某条旧断言与**已接受的 PRD / tech-m* 文档**冲突时，已接受文档胜出，按下述规则处理：

1. 在引入新语义的同一切片（同一提交）内，把测试改写到新语义。
2. 任务完成总结里记录：被改测试名、旧断言、新断言、依据的文档条款。
3. 禁止把测试改弱（删断言、放宽条件）来迁就实现；改写后必须覆盖同一路径。

先例：task 226（`tests/test_172cr_foreshadowing_resolve.py`、`tests/test_241_foreshadowing_resolved_trace.py`、`tests/test_settlement_extractor.py` 的 resolve 直写 `resolved` 断言 → 提案语义，依据 tech-m2 §3.2 / §4.3.3 / B3）。

## Where V1.0 tests go

After the owner accepted the PRD (2026-11-01), put new tests next to the behavior:

```text
tests/<area>/test_<behavior>.py
```

Examples: `tests/plan_checks/test_pending_not_in_bible.py`, `tests/cli/test_canon_show.py`.

Forbidden for new files:

- `test_task###_*.py`
- `test_<digits>_*.py` and `test_<digits><letter>_*.py`
- `test_v<digits>_*.py`
- any filename containing `task` plus a number (`test_settlement_extractor_task134.py` is the frozen exception)

Do not add another genre-specific recall pack. Do not grow `tests/evals/` and expect CI to run it.

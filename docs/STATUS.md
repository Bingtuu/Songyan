# Songyan Status

This page is the public status board for developers evaluating or contributing to Songyan.

Package version for this tip: **0.5.0** (owner name **v0.5**). This page does not cut a git tag.

## Release Readiness

| Area | Status |
|------|:------:|
| Source install | PASS |
| Wheel build | PASS |
| Wheel-installed CLI from non-repository cwd | PASS |
| Package resource loading | PASS |
| SQLite schema initialization | PASS |
| Template project creation | PASS |
| Accepted manuscript export smoke | PASS |
| CLI tests / full pytest / ruff / runtime mypy | PASS |
| Real LLM Ch1-3 release smoke | PASS on `eaa6bef` (2026-10-26, #20). Formal tag is a maintainer decision |

Current public status: **v0.5** (`0.5.0`) is a usable technical preview. It has Ch1–3 smoke evidence and does not claim that runs of 10 or more chapters are validated. The real LLM Ch1-3 smoke on main `eaa6bef7721e43ccd1b53be2280076a355842d9b` (PR #20, 2026-10-26, Asia/Shanghai) passed; `58d3621` (PR #21) records that result. A formal release tag is still a maintainer decision after merge and CI. The earlier FAIL on `11c4c761` (PR #19) stays as history.

## What Works

- Local-first Python CLI.
- SQLite-backed long-term project memory.
- Packaged genre profiles and project templates.
- `doctor` environment and resource checks.
- `create-project`, `run`, `report`, `metrics`, `five-gate`, `t9`, `bundle-run`, `export`, `backup`, `restore`.
- Profile safety tools: `validate`, `upsert --dry-run`, `history`, `rollback`.
- Per-role LLM model routing (`LLM_<ROLE>_*`) with per-role token/cost split in run reports.
- Import pipeline for existing novels: `import` command group (`ingest` / `segment` / `confirm` / `status` / `replay` / `synthesize` / `publish`) with manual confirmation gates, idempotent chapter replay with settlement extraction, and a lifecycle gate that blocks `run` until publish.
- Settlement write path hardened: degraded blocks are SAVEPOINT-isolated within the accept transaction, sqlite3.Error failures are logged via structlog, and transaction-aborting errors (e.g. SQLITE_FULL/IOERR) fail the chapter instead of silently accepting it with a corrupted fact base.
- Foreshadowing resolution traceability: `resolved_chapter` / `resolved_version_id` columns on `foreshadowings` (write-only, no gate-caliber change).
- Schema migrations run from a single ordered `_MIGRATIONS` registry shared by `init_schema` and `run_migrations`.
- Redacted diagnostic bundle for reproducible issue reports.
- CI for ruff, runtime mypy, pytest, CLI tests and wheel smoke.

## Validation Background

Internal long-window validation has covered:

- sci-fi baseline at 200+ chapters.
- xuanhuan, wuxia and urban samples at 200 accepted chapters.
- frozen guardrails for CED evidence scope, T9 cleanliness, five-gate semantics and SQLite fact persistence.

These historical validation records are not part of the public main documentation tree. Public release decisions should rely on the current release checklist, CI and reproducible smoke commands.

## Known Limits

- Songyan is a CLI system, not a web app or hosted service.
- Running real generation requires an LLM API key and may incur cost.
- Real LLM Ch1-3 smoke on main `eaa6bef7721e43ccd1b53be2280076a355842d9b` (PR #20 squash, 2026-10-26, Asia/Shanghai) passed. Project `5a7f3a4263bc499d95109ea460aa79df` (scifi template; create-project title 《轨道蜃景》). Run `run-552b2c04` exited 0 with status=completed. Ch1–3 were all accepted. There were no `settlement_review` or missing_facts failures. ContextEmergency appeared only as a streak warning, with no AutoHalt. Owner cost was ¥1.035 total (¥2/M input, ¥8/M output); the most expensive chapter was about ¥0.400. The ¥7.66 stop threshold was not hit. Box paths are in [HANDOFF-mew.md](HANDOFF-mew.md) only; the DB, logs, and manuscript are not in this repository. The smoke gate for a formal tag is met for this tip. A formal release tag is still a maintainer decision. Technical preview / release-candidate may proceed with this evidence. There is no further `settlement_review` fix knife.
- Historical: the real LLM Ch1-3 smoke on main `11c4c761` (PR #19, 2026-10-26, Asia/Shanghai) failed. Only Ch1 was accepted. Ch2 and Ch3 failed `settlement_review` because the summary was missing 主角决策/认知变化. The primary run `run-e98414fc` exited non-zero with `AutoHaltException` (ContextEmergency streak on Ch1–3); Ch2 also has retry `run-3defb98a`. Owner cost was ¥0.874 (Ch1 ¥0.208 / Ch2 ¥0.406 including the retry / Ch3 ¥0.260). The ¥7.66 stop threshold was not hit. Partial pass: doctor, create-project, report, bundle hygiene (no `.env`, keys, or manuscript), and one Markdown export. Artifacts for that fail stay on the maintainer box at `/workspace/songyan-release-smoke-out/` (`smoke_result.json`, `notes.md`, and the reports, bundles, and exports named in `smoke_result.json`), not in this repository. That run blocked a formal tag at the time. The `eaa6bef` rerun above is the current evidence.
- The import pipeline (`songyan import`) has full automated test coverage and CLI smoke evidence, but its real-LLM acceptance run (import a real manuscript, then continue writing) is still pending; treat imported-project continuation quality as unverified until that acceptance report lands.
- Research / report-only evaluation modules are not runtime release gates.

## Public Docs

| File | Purpose |
|------|---------|
| [README](../README.md) | Project overview and Quickstart |
| [Quickstart](quickstart.md) | Install, configure and run |
| [Troubleshooting](troubleshooting.md) | Failure recovery guide |
| [Release Checklist](release-checklist.md) | Maintainer release gate |
| [Quality Gates Methodology](quality-gates.md) | CED / T9 / five-gate definitions, threshold provenance and reproduction commands |
| [Ch200 Baseline Results](baseline-results.md) | Redacted aggregate results of the 4-genre 200-chapter validation |
| [Minimal Reproduction Guide](minimal-repro.md) | Issue reporting and diagnostics |
| [Documentation Index](INDEX.md) | Public documentation map |
| [Changelog](../CHANGELOG.md) | Release notes |
| [Contributing](../CONTRIBUTING.md) | Contribution workflow |

## Maintainer Next Steps

1. The smoke gate for a formal tag is met on `eaa6bef` (`run-552b2c04`, exit 0, Ch1–3 accepted). Do not open another `settlement_review` fix. The `11c4c761` / PR #19 fail stays on record.
2. Cutting a formal release tag is still a maintainer decision. Technical preview / release-candidate may proceed with the `eaa6bef` evidence. This page does not cut the tag.
3. Confirm no `.env`, local DB, logs, backups, bundles or private manuscripts are staged.

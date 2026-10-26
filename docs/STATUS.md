# Songyan Status

Public status board for developers evaluating or contributing to Songyan.

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
| Real LLM smoke | Ch1–3 gate **PASS** on `eaa6bef` (#20). Ch1–10 on `47954cb`: **pipeline PASS**, **DG-1 fail**, **literary fail**. Formal tag is a maintainer decision |

**v0.5** (`0.5.0`) is a usable technical preview. **Gates** are validated through Ch10 on `47954cb`; **literary quality is not** (human read failed). Ch1–3 gate PASS on `eaa6bef`; earlier `11c4c761` fail recorded in #19/#21.

## What Works

- Local-first Python CLI, SQLite project memory, packaged profiles and templates, `doctor`.
- `create-project`, `run`, `report`, `metrics`, `five-gate`, `t9`, `bundle-run`, `export`, `backup`, `restore`.
- Profile `validate` / `upsert --dry-run` / `history` / `rollback`. Per-role `LLM_<ROLE>_*` routing and cost split.
- Import (`ingest`, `segment`, `confirm`, `status`, `replay`, `synthesize`, `publish`) with confirmation gates; `run` stays blocked until publish.
- SAVEPOINT-isolated settlement writes; aborting sqlite errors fail the chapter. Foreshadowing resolution columns are write-only. One `_MIGRATIONS` registry.
- Redacted diagnostic bundles. CI: ruff, runtime mypy, pytest, CLI tests, wheel smoke.

## Validation Background

Not in the public tree: sci-fi 200+ chapters; xuanhuan, wuxia, and urban at 200 accepted chapters; frozen CED, T9, five-gate, and SQLite fact guardrails. Release decisions use the checklist, CI, and reproducible smoke.

## Known Limits

- CLI only, not a hosted service. Real generation needs an API key and spends money.
- Ch1–10 on `47954cb` (scifi 《轨道蜃景》, `run-33841231`): 10/10 accepted; QG, settlement, summary, and export OK; exit 0. **DG-1 failed** (avg revision 1.7 > 1.5; ContextEmergency on all 10 chapters; no AutoHalt). Owner cost ~¥3.413 (¥2/M in, ¥8/M out); max chapter ¥0.474; ¥7.66 stop not hit.
- Human read of that export **failed**: Ch1→Ch2 timeline rollback, Hermes/赫耳墨斯 name drift, 3-year vs 417-day vs “沈岚此刻…四光年”, repeated oxygen-threat and EVA-resonance beats, English leak `ninety-two 秒`.
- Real-LLM import-then-continue is still pending. Research modules are not runtime release gates.

Identifiers and box paths: [HANDOFF-mew.md](HANDOFF-mew.md).

## Public Docs

| File | Purpose |
|------|---------|
| [README](../README.md) | Project overview and Quickstart |
| [V1.0 PRD](prd-v1-writing-assist.md) | Planning for the human-led writing assistant. Not implemented on this tip |
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

1. Cite the `47954cb` Ch1–10 run as pipeline evidence only. Literary quality failed the human read. Do not open another `settlement_review` fix for the `11c4c761` fail.
2. A formal release tag is still a maintainer decision. This page does not cut the tag.
3. Confirm no `.env`, local DB, logs, backups, bundles, or private manuscripts are staged.

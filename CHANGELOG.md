# Changelog

All notable changes to Songyan are recorded here.

## 0.5.0 - 2026-10-26

Owner Bingtuu named this tip **v0.5**. Package metadata is `0.5.0`. This entry records the name and the README; it does not create a git tag.

### Changed

- README rewritten so a new visitor can see what Songyan is, how to install and run it, what v0.5 has actually shown, and where the limits are.
- `pyproject.toml` and `songyan.__version__` aligned to `0.5.0`. They previously disagreed (`2.0.0` and `0.1.0`).
- Version examples in `docs/minimal-repro.md` and the bug-report template now say `0.5.0`.

### Status

- Usable preview. The real-LLM sci-fi Ch1–3 release smoke **PASS** is the run on main `eaa6bef` (PR #20), recorded on main by `58d3621` (PR #21). Project `5a7f3a4263bc499d95109ea460aa79df`, run `run-552b2c04`, exit 0, Ch1–3 accepted. Formal runs of 10 or more chapters are not yet validated on this tip.
- Plan-first Phases A–C are closed on main. Phase C 都市灵异 recall did not meet the exit (1/5). Operating conclusion: a human maintains the fact bible, and the model writes to it. `SettlementExtractor` still writes the settlement store and is not plan canon.
- The earlier Ch1–3 fail on `11c4c761` (PR #19) stays as history.
- Owner cost basis in these records: ¥2/M input, ¥8/M output. Documented per-chapter stop line for those runs: ¥7.66.

### Notes

- License remains AGPL-3.0.
- Historical 2.0.0 notes below describe the 2026-08 open-source readiness drop. v0.5 is the owner's name for the current tip, not a claim that long-form generation was re-validated.

## 2.0.0 - 2026-08-02

### Added

- Open-source readiness path:
  - Quickstart and troubleshooting documentation for external technical users.
  - `songyan doctor` structured checks for config, DB/schema, resources, logs, budget and LLM prerequisites.
  - `songyan run` preflight and non-zero exit behavior for failed runs.
  - `songyan backup` / `songyan restore` project asset lifecycle commands.
  - Standardized failure recovery advice across run, doctor, report, export, backup and restore.
  - `songyan bundle-run` redacted diagnostic bundle.
  - `songyan profile validate`, `profile upsert --dry-run`, `profile history` and `profile rollback`.
  - Release checklist, minimal reproduction guide and issue template.

### Validated

- Long-window baselines remain the current quality evidence:
  - sci-fi Ch200 baseline frozen.
  - xuanhuan / wuxia / urban Ch200 accepted=200, gap=0, five-gate PASS, segment audit PASS, T9=0.
- Release wheel smoke passed on Windows:
  - wheel build succeeded.
  - wheel-installed CLI ran from a non-repository cwd.
  - package resources loaded through `doctor`.
  - template project creation and accepted manuscript export passed.

### Notes

- Songyan is released under AGPL-3.0.
- This release focuses on open-source usability and release discipline; it does not expand generation capability.
- Research / report-only signals remain outside prompt, CED and hard gate paths.

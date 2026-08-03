# Changelog

All notable changes to Songyan are recorded here.

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

# Songyan Status

This page is the public status board for developers evaluating or contributing to Songyan.

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
| Real LLM Ch1-3 release smoke | Maintainer must rerun before formal release tag |

Current public status: Songyan is ready as a technical preview / release-candidate for external developers. A formal release tag should be cut only after the maintainer reruns [Release Checklist](release-checklist.md) on the target commit, including a real LLM Ch1-3 smoke.

## What Works

- Local-first Python CLI.
- SQLite-backed long-term project memory.
- Packaged genre profiles and project templates.
- `doctor` environment and resource checks.
- `create-project`, `run`, `report`, `bundle-run`, `export`, `backup`, `restore`.
- Profile safety tools: `validate`, `upsert --dry-run`, `history`, `rollback`.
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
- The maintainer must rerun real LLM Ch1-3 smoke before a formal release tag.
- Research / report-only evaluation modules are not runtime release gates.

## Public Docs

| File | Purpose |
|------|---------|
| [README](../README.md) | Project overview and Quickstart |
| [Quickstart](quickstart.md) | Install, configure and run |
| [Troubleshooting](troubleshooting.md) | Failure recovery guide |
| [Release Checklist](release-checklist.md) | Maintainer release gate |
| [Minimal Reproduction Guide](minimal-repro.md) | Issue reporting and diagnostics |
| [Documentation Index](INDEX.md) | Public documentation map |
| [Changelog](../CHANGELOG.md) | Release notes |
| [Contributing](../CONTRIBUTING.md) | Contribution workflow |

## Maintainer Next Steps

1. Rerun [Release Checklist](release-checklist.md) on the target release commit.
2. Record real LLM Ch1-3 smoke results in release notes.
3. Confirm no `.env`, local DB, logs, backups, bundles or private manuscripts are staged.

# Contributing to Songyan

Songyan welcomes focused engineering contributions that improve reliability, documentation, packaging, diagnostics and reproducibility.

## Read this first

[AGENTS.md](AGENTS.md) is the contributor and agent contract. The product plan is [docs/prd-v1-writing-assist.md](docs/prd-v1-writing-assist.md) (human-led writing assistant). Package tip stays **0.5.0**. “V1.0” is a product-generation name, not a version bump.

Plan-first phases A–C are closed. The short pointer is [docs/ROADMAP-plan-first.md](docs/ROADMAP-plan-first.md). Do not load `docs/archive/` for a normal change. Do not treat the old Task 001–019 handbook as a live queue.

The daily entry, when there is one, is [docs/HANDOFF-mew.md](docs/HANDOFF-mew.md), then `tasks/` after the owner opens that queue. Do not extend extract-then-patch or add genre-specific checkers as the main path. Literary quality stays with the human. Do not claim proposed CLI commands in the README.

## Project Boundary

- SQLite is the only long-term source of truth.
- Generated and revised chapter versions are append-only.
- Confirm-to-canon: extracts and settlement summaries are proposals until a person confirms them.
- CED, T9, five-gate and hard gate rules are not casual extension points.
- Prompt cards live under `src/songyan/prompts/cards/`; do not embed long prompts in code.

Open-source contributions should preserve these runtime boundaries unless a proposal explicitly includes regression evidence.

Test layout and the ban on new `test_task###` filenames: [tests/README.md](tests/README.md).

## Before Opening a PR

Run:

```powershell
python -m pytest tests/ -q
python -m pytest tests/cli -q
ruff check src/ tests/
```

If tests may hang on Windows, use:

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 900 -- python -m pytest tests/ -q
```

For packaging changes, also run:

```powershell
python -m pip wheel . --no-deps -w .tmp/task215-wheel
```

## Documentation Expectations

Update the relevant public entry points when behavior changes:

- `README.md` (visitor-facing only; do not put the task log here)
- `AGENTS.md` when the contributor contract changes
- `docs/quickstart.md`
- `docs/troubleshooting.md`
- `docs/STATUS.md`
- `docs/HANDOFF-mew.md`
- `docs/INDEX.md`

For release-impacting changes, update:

- `CHANGELOG.md`
- `docs/release-checklist.md`
- `docs/minimal-repro.md`

## Privacy and Security

Never commit:

- `.env`
- API keys or tokens
- raw private manuscripts
- local DB files
- logs, run bundles or backups containing private data

Use `songyan bundle-run` for redacted diagnostics:

```powershell
songyan bundle-run --run-id <run_id> --output bundles/
```

## Issue Reports

Use the bug report template. Include:

- Songyan version or commit
- OS and Python version
- install method
- command and exit code
- `songyan doctor --json --init-db` output
- run bundle or minimal reproduction steps

See `docs/minimal-repro.md`.

## License

By contributing, you agree that your contribution is licensed under AGPL-3.0, matching the project license.

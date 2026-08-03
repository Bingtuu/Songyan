# Contributing to Songyan

Songyan welcomes focused engineering contributions that improve reliability, documentation, packaging, diagnostics and reproducibility.

## Project Boundary

Songyan is a long-form Chinese fiction generation system with strict data and quality boundaries:

- SQLite is the only long-term source of truth.
- Generated and revised chapter versions are append-only.
- Writer drafts; RevisionHandler patches; auditors diagnose.
- CED, T9, five-gate and hard gate rules are not casual extension points.
- Prompt cards live under `src/songyan/prompts/cards/`; do not embed long prompts in code.

Open-source contributions should preserve these runtime boundaries unless a proposal explicitly includes regression evidence.

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

- `README.md`
- `docs/quickstart.md`
- `docs/troubleshooting.md`
- `docs/STATUS.md`
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

# Songyan Documentation

Public documentation map for users and contributors.

## Start Here

| Document | Purpose |
|----------|---------|
| [README](../README.md) | Project overview, features and shortest path |
| [Status](STATUS.md) | Current release readiness and known limits |
| [Quickstart](quickstart.md) | Install, configure, run and export |
| [Troubleshooting](troubleshooting.md) | Common failures and recovery commands |

## Release and Contribution

| Document | Purpose |
|----------|---------|
| [Release Checklist](release-checklist.md) | Maintainer release gate and smoke commands |
| [Minimal Reproduction Guide](minimal-repro.md) | How to file actionable issues |
| [Contributing](../CONTRIBUTING.md) | Contribution workflow and project boundaries |
| [Changelog](../CHANGELOG.md) | Release notes |
| [License](../LICENSE) | AGPL-3.0 license |

## Architecture References

| Document | Purpose |
|----------|---------|
| [Engineering Notes](architecture/04-vibe-coding-engineering.md) | Engineering model and workflow notes |
| [Technical Reference](architecture/05-tech-reference.md) | Technical reference for deeper contributors |

## Runtime Artifacts

Songyan creates local runtime artifacts that should not be committed:

- `songyan.db`, `*.db`, `*.sqlite`
- `logs/`
- `exports/`
- `backups/`
- `bundles/`
- `.env`

Use `songyan bundle-run --run-id <run_id> --output bundles/` when you need a redacted diagnostic package for issue reports.

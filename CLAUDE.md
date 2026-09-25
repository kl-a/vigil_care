# Vigil

Clinical decision support for oncologists. Start with [docs/Vigil_Design_Document.md](docs/Vigil_Design_Document.md) (v1.3) and the glossary in [CONTEXT.md](CONTEXT.md). Frontend work follows [docs/frontend-design.md](docs/frontend-design.md).

## Database changes keep the docs in step

Any change to a table, column, constraint, index, grant or relationship must update all of the following **in the same change**:

1. **The SQLAlchemy models and an Alembic migration.** The drift test fails if they disagree.
2. **The data-model diagram.** Run `make erd` to regenerate [docs/data-model/](docs/data-model/index.html). `make ci` fails if it's stale.
3. **Design doc §6.** Update §6.1 (the overview diagram, if a relationship changed), §6.2 (conventions, CHECK values, roles, tables that never change) and §6.3 (the table catalogue).
4. **[CONTEXT.md](CONTEXT.md)**, if a domain term is added, renamed or retired.

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues on `kl-a/vigil_care` (use the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

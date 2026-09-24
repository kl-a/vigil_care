# The MVP runs locally, built to move to Azure

The MVP runs entirely on practice machines, but later versions will move some or all of Vigil to Azure for managed storage, backup and scalable compute. We therefore put each piece of infrastructure behind a swappable interface now: file storage (local disk → Blob Storage), database (Postgres in Docker → Azure Database for PostgreSQL), OCR/VLM worker (local HTTP worker → GPU VM or container app), job queue, encryption keys (local keystore → Key Vault) and login (local accounts → Entra ID). The pieces are cheap to add now and expensive to retrofit. We are deliberately **not** building multi-tenancy yet.

## Consequences

- The Practice Boundary is defined as infrastructure the practice controls, not physical machines, so [ADR 0001](0001-deidentify-before-leaving-practice.md) holds unchanged after the move.
- Anything that assumes local-only operation (offline use, disk paths, `.env` keys) must go through these interfaces, never around them.

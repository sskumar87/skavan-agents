# Delivery progress

This is the current execution ledger. It is updated when a component has been verified, not merely drafted.

## Completed

| Component | Evidence |
| --- | --- |
| Product database | Separate `skavan` database created on Laptop 1; existing `skav` database remains untouched. |
| Database roles | `skavan_app` is a restricted runtime login; `skavan_migrator` owns the product database and is used only for schema migration. |
| pgvector baseline | `vector` 0.8.1 enabled; `vector(1536)` group-memory column and cosine HNSW index validated. |
| Alembic baseline | Revision `20260821_0001` applied forward-only to `skavan` after a disposable-database validation run. |
| Backup and restore rehearsal | A custom-format backup of the empty baseline database was restored into an isolated disposable database; revision `20260821_0001` was verified, then the disposable databases were removed. |
| Local backup automation | Backup script generated and checksummed a fresh `skavan` dump on Laptop 1 without touching the existing `skav` database. |
| Reproducible app builds | Latest stable web/API dependencies are locked; production Dockerfiles, health checks and Hermes outbound-only egress are defined. API tests and the Next.js standalone build pass. |
| PostgreSQL network binding | Docker port 5432 is bound to Laptop 1 private address only, preserving Laptop 2 access. |
| Infrastructure source | Laptop 2 Compose, private ingress and Cloudflare Tunnel templates are committed; public Hermes/PostgreSQL routes are absent. |

## In progress

| Component | Next action |
| --- | --- |
| Laptop 1 network hardening | Confirm approved Redis/Redis Insight consumers before changing their all-interface bindings. |
| Backups and recovery | Install the verified service/timer, then choose encrypted off-host destination, recovery-key custody and recovery objectives before enabling scheduled backups. |
| Laptop 2 deployment | Reviewed release tags and immutable multi-platform digests are recorded. Complete vendor-specific ZITADEL configuration and run Docker Compose/build validation on Laptop 2. |
| Identity ingress | Choose app/auth hostnames and implement verified ZITADEL public OIDC routing while keeping administration private. |

## Not started

| Component | Dependency |
| --- | --- |
| API foundation and identity bridge | Runnable ZITADEL configuration and Laptop 2 build images |
| Groups, threads and Hermes streaming | API foundation and verified Hermes API contract |
| Shared group memory application flow | API authorization layer; database storage is ready |
| Normal-user UI | Stable identity/API contracts; use the documented responsive theme system |

## Decisions still required

1. Public application and OIDC hostnames.
2. Encrypted off-host backup destination, key custody, schedule and recovery objectives.
3. Approved/pinned ZITADEL and Hermes releases, including their image digests.
4. Whether Redis/Redis Insight require any LAN access beyond Laptop 1.

Until these decisions are made, no API/UI feature is treated as deployable. The infrastructure work continues without exposing secrets or enabling public management routes.

# Delivery progress

This is the current execution ledger. It is updated when a component has been verified, not merely drafted.

## Completed

| Component | Evidence |
| --- | --- |
| Product database | Separate `skavan` database created on Laptop 1; existing `skav` database remains untouched. |
| Database roles | `skavan_app` is a restricted runtime login; `skavan_migrator` owns the product database and is used only for schema migration. |
| ZITADEL database | Dedicated `zitadel` database and non-superuser owner created on Laptop 1; its DSN is stored only in a protected remote env file and its initial checksum-protected backup was verified. |
| pgvector baseline | `vector` 0.8.1 enabled; `vector(1536)` group-memory column and cosine HNSW index validated. |
| Alembic baseline | Revision `20260821_0001` applied forward-only to `skavan` after a disposable-database validation run. |
| Backup and restore rehearsal | A custom-format backup of the empty baseline database was restored into an isolated disposable database; revision `20260821_0001` was verified, then the disposable databases were removed. |
| Local backup automation | Docker Desktop user timers are installed for `skavan` and `zitadel`; both scoped-role jobs completed with valid checksums and the script rejects the existing `skav` database. |
| Reproducible app builds | Latest stable web/API dependencies are locked; production Dockerfiles, health checks and Hermes outbound-only egress are defined. API tests and the Next.js standalone build pass. |
| Clean-machine CI | GitHub Actions run 32447450529 passed API tests, web audit/type-check/build, full Compose-profile validation and both production container builds. |
| PostgreSQL network binding | Docker port 5432 is bound to Laptop 1 private address only, preserving Laptop 2 access. |
| Infrastructure source | Laptop 2 Compose, private ingress and Cloudflare Tunnel templates are committed; public Hermes/PostgreSQL routes are absent. |
| ZITADEL application registration | `Skavan Platform` project and `Skavan Web` Authorization Code + PKCE client created with exact `https://skavan.skavapp.com` callback/logout URIs; no client secret or product-role claims are enabled. |
| Public authentication | ZITADEL login and federated logout are working through the two Cloudflare Tunnel hostnames. |
| V1 UI contract | Authenticated workspace prototype approved; four semantic CSS themes and responsive/accessibility development rules are locked in `docs/architecture/ui-design-system.md`. |

## In progress

| Component | Next action |
| --- | --- |
| Laptop 1 network hardening | Confirm approved Redis/Redis Insight consumers before changing their all-interface bindings. |
| Backups and recovery | Enable user lingering for unattended timers, then choose encrypted off-host destination, recovery-key custody, disk/backup-failure alerting, retention and recovery objectives before production use. |
| Laptop 2 deployment | Reviewed release tags and immutable multi-platform digests are recorded. Recreate the web/identity services with the protected environment and run the on-machine Compose validation. |
| Product user synchronization | FastAPI verifies the ZITADEL ID token and idempotently links immutable issuer/subject identities to canonical product users. Rebuild the API/web containers and complete one live login/database check. |

## Not started

| Component | Dependency |
| --- | --- |
| Groups, threads and Hermes streaming | API foundation and verified Hermes API contract |
| Shared group memory application flow | API authorization layer; database storage is ready |
| Normal-user UI | Stable identity/API contracts; use the documented responsive theme system |

## Decisions still required

1. Encrypted off-host backup destination, key custody, schedule and recovery objectives.
2. Whether Redis/Redis Insight require any LAN access beyond Laptop 1.

Until these decisions are made, no API/UI feature is treated as deployable. The infrastructure work continues without exposing secrets or enabling public management routes.

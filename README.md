# Skavan Agents

Multi-user web platform around the Hermes agent runtime.

## Status

Foundation only. The first vertical slice is signup and login through group/thread chat, with the backend brokering all Hermes communication.

## Repository layout

- `apps/web` — Next.js client
- `apps/api` — FastAPI modular monolith
- `packages/shared` — cross-client API contracts
- `database/migrations` — Alembic migration source
- `infra` — local service configuration
- `docs` — architecture decisions and delivery plan
- `tests/e2e` — whole-product safety and workflow tests

Read [the architecture overview](docs/architecture/overview.md) and [the implementation plan](docs/implementation-plan/README.md) before extending the platform.

## Database foundation

The product database is managed only through Alembic. See [database migration instructions](database/migrations/README.md) for the V1 schema, required pgvector extension, and safe local validation steps.

## Local development

Prerequisites and service configuration are intentionally introduced with the first runnable vertical slice. Do not expose Hermes credentials or call Hermes from the browser.

## Guardrails

- Product users, groups, threads, authorization and shared group memory belong to this platform.
- Hermes remains the agent runtime; its dashboard is operator-only.
- PostgreSQL is authoritative for collaborative thread history.
- Group-scoped memory retrieval must authorize before semantic search.

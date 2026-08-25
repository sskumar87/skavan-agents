# Database migrations

Alembic is the only mechanism that changes the product schema. Every merged or deployed revision is immutable. Review generated migrations before committing them; do not rely on application startup to create tables.

## Scope

`20260821_0001_product_baseline` establishes PostgreSQL tables for product users and OIDC identities, collaboration groups and memberships, threads and authoritative messages, group-scoped vector memory, channel identity mappings, Hermes profile bindings, capability permissions, business approvals, and audit events. It enables `pgvector` before creating the group-memory vector index.

The `group_memories.embedding` contract is `vector(1536)` in V1. A model change that requires another dimension is a deliberate schema migration and index rebuild, not a configuration-only change.

## Local usage

Use the dedicated table-owner role for migrations. In this deployment the roles
are deliberately separate:

- `skavan_app` is the restricted API runtime account. It cannot alter tables.
- `skavan_migrator` owns the product tables and is the only account Alembic uses.
- `skav_user` is the Laptop 1 database administrator and is used only for
  initial provisioning or recovery, never by the application.

Laptop 2 stores both connection strings in the protected phase-one environment
file. `DATABASE_URL` contains `skavan_app`; `SKAVAN_MIGRATION_DATABASE_URL`
contains `skavan_migrator`. Never substitute the runtime URL when running
Alembic. Use the checked-in wrapper from the repository root:

```powershell
.\infra\laptop2\run-product-migrations.ps1
```

The wrapper loads the protected migration URL without displaying it, verifies
that it names `skavan_migrator`, applies the forward migration, and prints the
resulting Alembic revision.

For a disposable local database, set a migration connection string outside
source control:

```powershell
$env:SKAVAN_MIGRATION_DATABASE_URL = 'postgresql+asyncpg://skavan_migrator:local-password@localhost:5432/skavan'
alembic -c database/migrations/alembic.ini upgrade head
```

`SKAVAN_MIGRATION_DATABASE_URL` takes precedence. Legacy
`SKAVAN_DATABASE_URL` and `DATABASE_URL` fallbacks exist only for disposable
development environments. The URL must use `postgresql+asyncpg`; no credentials
or connection strings belong in committed files.

Useful checks:

```powershell
alembic -c database/migrations/alembic.ini current
alembic -c database/migrations/alembic.ini check
alembic -c database/migrations/alembic.ini downgrade -1
alembic -c database/migrations/alembic.ini upgrade head
```

Run the downgrade/upgrade cycle only against a disposable local database. Shared and deployed databases only move forward through reviewed migrations.

## Required validation before merge

1. Create a fresh disposable PostgreSQL database with pgvector available. On the selected TimescaleDB image, enabling `vector` requires a PostgreSQL superuser: enable it once in the target database before the Alembic run, then use the separate restricted migration role for schema changes. The runtime role must remain restricted.
2. Run `upgrade head`, `current`, and [`validate.sql`](validate.sql) with `psql`, for example: `psql "$env:POSTGRES_URL" -v ON_ERROR_STOP=1 -f database/migrations/validate.sql`.
3. Run `alembic check`; it should report no model metadata changes until ORM metadata is introduced.
4. Run the downgrade/upgrade cycle against the disposable database.
5. For memory work, add an integration test proving the application authorizes membership and group scope before it issues a vector search. A database index cannot enforce that authorization rule by itself.

## Future revisions

Create revisions with `alembic -c database/migrations/alembic.ini revision -m "describe change"`. Autogeneration may be enabled when the API metadata exists, but the emitted migration is always a review artifact. Do not edit a revision after it is merged or deployed.

# Database migrations

Alembic is the sole source of truth for database schema changes. Migrations are immutable once merged or deployed. The initial migration will explicitly enable the `vector` extension before creating group-memory tables.

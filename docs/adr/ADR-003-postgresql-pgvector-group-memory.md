# ADR-003: PostgreSQL + pgvector for shared group memory

**Status:** Accepted

V1 stores scoped shared memory in PostgreSQL with pgvector. Membership and group scope are checked before every semantic search; cross-group retrieval is prohibited.

# Implementation plan

Work in thin vertical slices, with tests added alongside each slice.

1. **Foundation** — repository, architecture records, service boundaries and migration baseline.
2. **Identity** — ZITADEL OIDC sign-up/login and backend session validation.
3. **Groups** — memberships, roles and server-side authorization.
4. **Threads** — group threads, messages and authoritative PostgreSQL history.
5. **Hermes chat** — backend adapter, constrained context and streamed responses.
6. **Group memory** — pgvector storage and authorization-first retrieval.
7. **Permissions** — skill/MCP mappings and approval bridging.
8. **Workflows** — Hermes delegation and Kanban evaluation.
9. **Channels** — Telegram first, then WhatsApp, linked to canonical users.
10. **Hardening** — audit, backups, monitoring and security review.

## First milestone acceptance criteria

`Signup → Login → Create group → Create thread → Send message → Authorize → Hermes → Stream response → Persist conversation`

## Second milestone acceptance criteria

A durable fact saved in one Group X thread can be recalled in another Group X thread. It cannot be retrieved by Group Y, or by a user removed from Group X. These isolation tests are release-blocking.

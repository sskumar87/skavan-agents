# Architecture overview

Skavan Agents is a multi-user product built around Hermes. Hermes provides the AI/agent runtime. The product controls its own identity, collaboration, authorization, product approvals and audit trail.

## Boundary of responsibility

| Platform-owned | Hermes-owned |
| --- | --- |
| Users, groups, memberships and roles | Agent runtime and profiles |
| Threads and authoritative collaborative history | Skills, MCP, tools and provider integrations |
| Group-scoped shared memory | Personal/profile memory (`USER.md`, `MEMORY.md`) |
| Business authorization, approvals and audit | Agent/tool approval mechanics |
| Channel identity mapping | Gateway, delegation, Kanban and Cron |

The web browser communicates only with the FastAPI backend. The backend validates identity and group authorization, resolves a constrained Hermes execution context, and makes private Hermes API calls. API server keys never enter browser code.

## Product data model

PostgreSQL is the source of truth for product entities: users, identity accounts, groups, memberships, threads, messages, group memories, channel identities, Hermes profile bindings, permission mappings, approvals and audit events.

Threads are product entities, not Hermes profiles. A Hermes profile may supply an isolated personal or agent context but must not stand in for a collaboration group.

## Authorization model

Authentication is supplied by ZITADEL using OIDC. The immutable OIDC `sub` is the canonical external identity key. Product authorization is evaluated by the backend with roles `OWNER`, `ADMIN`, `MEMBER` and `VIEWER`.

Effective agent capability is the intersection of Hermes capability, user permission and group permission. Normal users never receive unrestricted host, filesystem, credential, global configuration or global scheduling access.

## Shared memory

V1 uses PostgreSQL with pgvector. Before every vector search, the backend verifies membership and group scope. Retrieved memories always carry their `group_id`; cross-group recall is prohibited. Same-group cross-thread recall is selective, not a wholesale transcript import.

## Deployment shape

Laptop 1 is the private PostgreSQL + pgvector and backup node. Laptop 2 runs the web UI, FastAPI, ZITADEL, Hermes, and reverse proxy. Only reverse-proxy HTTPS is public; Hermes APIs remain private. Docker Compose is sufficient for V1.

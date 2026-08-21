# Development work breakdown

This plan keeps work independently reviewable. A component may begin only when its listed dependencies are accepted; API and normal-user UI work deliberately follow the infrastructure/database foundation.

## Foundation: infrastructure and data

| ID | Component | Deliverable | Depends on |
| --- | --- | --- | --- |
| INF-01 | Service topology | Laptop 1/Laptop 2 service map, Compose structure, environment contract and internal networks | — |
| INF-02 | Private database access | documented private network path from Laptop 2 to PostgreSQL on Laptop 1; backups and connectivity checks | INF-01 |
| DB-01 | Migration framework | Alembic configuration, migration conventions and an upgrade validation command | — |
| DB-02 | Database baseline | explicit `vector` extension and immutable initial schema migration | DB-01 |
| DB-03 | Data safety | database roles, least-privilege application connection, backup/restore procedure and secret handling | DB-02, INF-02 |
| INF-03 | ZITADEL foundation | self-hosted service scaffold, database boundary, TLS/internal routing and bootstrap runbook | INF-01, INF-02 |
| INF-04 | Hermes boundary | private service routing, server-side credential contract, dashboard operator restriction | INF-01 |
| INF-05 | Public ingress | Cloudflare Tunnel connector, reverse-proxy route allowlist and no-public-Hermes verification | INF-01, INF-04 |
| INF-06 | Observability | structured logs, health endpoints, backups/alert checklist and deployment runbook | INF-01–05, DB-03 |

### Database entities in the baseline

The initial migration covers the product-owned schema only: users, identity accounts, groups, memberships/roles, threads, messages, group memories, channel identities, Hermes profile bindings, capability permissions, approvals and audit events. It does not create a custom Hermes skill, MCP or workflow registry.

## Backend vertical slices

| ID | Component | Deliverable | Depends on |
| --- | --- | --- |
| API-01 | Application foundation | FastAPI configuration, health/readiness, database session management, error envelope and test harness | DB-01, INF-01 |
| API-02 | Identity bridge | OIDC validation, user provisioning from immutable `sub`, BFF/session design and profile preferences endpoint | INF-03, DB-02 |
| API-03 | Group authorization | groups, memberships, OWNER/ADMIN/MEMBER/VIEWER policies and audit events | API-02 |
| API-04 | Threads | group-scoped thread/message commands and queries, with PostgreSQL history authoritative | API-03 |
| API-05 | Hermes adapter | constrained execution context, capability intersection, private calls, streaming and error normalisation | API-04, INF-04 |
| API-06 | Group memory | write/retrieval abstraction, authorization-before-vector-search and isolation tests | API-03, DB-02 |
| API-07 | Approvals and permissions | business approvals, skill/MCP mapping and Hermes approval bridge | API-05 |
| API-08 | Channels/workflows | canonical channel linking, delegation, Kanban/Cron authorization wrappers | API-02, API-07 |

## Web client vertical slices

| ID | Component | Deliverable | Depends on |
| --- | --- | --- |
| WEB-01 | Design system | shared app shell, tokens, four saved theme families with dark/daylight modes, responsive/accessibility checks | API-02 |
| WEB-02 | Identity and profile | signup/login/logout, current-user session and saved Appearance setting | API-02, WEB-01 |
| WEB-03 | Groups and threads | group switcher, membership-aware views, thread list and empty/error states | API-03, API-04, WEB-01 |
| WEB-04 | Chat | streamed messages, composer, agent status and reconnect/error handling | API-05, WEB-03 |
| WEB-05 | Memory and approvals | memory context affordance, approval cards and capability explanations | API-06, API-07, WEB-04 |
| WEB-06 | Connections | Telegram/WhatsApp linking UI after the web flow is stable | API-08, WEB-02 |

## Verification and release gates

| ID | Gate | Release-blocking check |
| --- | --- | --- |
| QA-01 | Migration safety | empty database can upgrade; schema version is current; pgvector extension is present |
| QA-02 | Infrastructure boundary | external ingress reaches only approved reverse-proxy routes; Hermes API/dashboard and PostgreSQL are not public |
| QA-03 | Identity and authorization | roles are enforced server-side and OIDC `sub`, not email, is the identity key |
| QA-04 | Memory isolation | same-group recall works; cross-group and removed-member recall fail before semantic search |
| QA-05 | First milestone | signup → login → group → thread → message → authorize → Hermes stream → persisted history |
| QA-06 | UI standard | all changed flows work on mobile/tablet/desktop, keyboard navigation and all supported theme modes |

## Immediate sequence

1. Finish and review DB-01/DB-02, INF-01, INF-04 and INF-05 in parallel.
2. Integrate those components and validate the private Laptop 1 ↔ Laptop 2 connectivity boundary.
3. Complete INF-03 and DB-03 before relying on authentication or application data.
4. Start API-01 only after migrations and service topology have been accepted.
5. Start WEB-01/API-02 together once identity contracts are stable.

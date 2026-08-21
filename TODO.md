# Delivery TODO

## Phase 1 — running now

- [x] FastAPI health endpoint
- [x] FastAPI server-side Hermes adapter
- [x] Responsive custom chat UI
- [x] Laptop 2 Docker and pinned Hermes image definition
- [x] Configure protected DeepSeek credentials and select `deepseek-chat`
- [ ] Optionally configure Anthropic as the fallback provider
- [x] Start Hermes, API and web on Laptop 2
- [x] Send one real UI message through FastAPI to Hermes
- [ ] Replace the non-streaming response with SSE streaming

## Important, deferred until the chat slice works

- ZITADEL login and immutable `sub` identity mapping
- PostgreSQL persistence for users, groups, threads and messages
- Group roles and authorization checks
- Shared pgvector memory and release-blocking cross-group isolation tests
- Persisted four-theme user preference
- Cloudflare Tunnel and final app/auth hostnames
- PostgreSQL TLS, firewall hardening and encrypted off-host backups
- Approvals, audit, skills/MCP permissions, Telegram and WhatsApp

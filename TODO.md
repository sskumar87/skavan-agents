# Delivery TODO

The detailed delivery evidence and architecture status live in
`docs/implementation-plan/progress.md`. This file is the concise actionable
backlog; completed milestones are recorded in the progress ledger rather than
left mixed with unfinished work.

## P1 — release and operational follow-up

- [ ] Correct the ZITADEL proxy health check and verify container health.
- [ ] Back up and independently restore the Personal and Work Hermes profiles.
- [ ] Verify Personal/Work memory isolation and same-profile memory sharing.
- [ ] Select encrypted off-host backup storage and complete a restore rehearsal.
- [ ] Update and test the clean-machine deployment runbook.
- [ ] Complete the Telegram pilot Connections UI and acceptance checks.
- [ ] Reconcile Telegram access automatically when a ZITADEL profile role is revoked.
- [ ] Add bounded Hermes gateway self-recovery and failure alerts.
- [ ] Register and verify the SKAV MCP service as an automatic Windows startup task.

## P3 — non-blocking extensions

- [ ] Design an explicit, idempotent importer for legacy PostgreSQL-only chats.
- [ ] Extend per-session writer coordination to supported direct Hermes clients.
- [ ] Provide a safe, read-oriented `/commands` allowlist for product users.
- [ ] Evaluate an optional secondary LLM provider and fallback policy.
- [ ] Evaluate a mechanical action-ledger observer without treating it as authorization.
- [ ] Add WhatsApp and other channels after the Telegram pilot is accepted.
- [ ] Add native mobile and voice clients on the existing backend contracts.

## Recently resolved operational incidents

- [x] Restored the Laptop 2 SKAV MCP service after the live XAU watchers lost their data source.
- [x] Changed the V2 watcher from unavailable `api_server` origin delivery to local silent delivery.
- [x] Verified both live XAU watcher jobs complete successfully on consecutive scheduler cycles.

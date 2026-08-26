# Delivery progress

Last updated: 2026-08-26

This is the project execution ledger. A component is marked complete only after
it has been implemented and verified. Material architecture changes require an
ADR before implementation.

## Current Phase 1 objective

Provide a stable, responsive multi-user web client for the Personal and Work
Hermes profiles, with authentication, saved user preferences and conversations
that can be continued from both Skavan and Hermes Web.

## Completed and deployed

| Component | Evidence |
| --- | --- |
| Product database | Separate `skavan` database exists on Laptop 1; the existing `skav` trading database remains untouched. |
| Database foundation | Restricted runtime/migration roles, pgvector 0.8.1 and Alembic revision `20260821_0001` are operational. |
| Public authentication | ZITADEL signup, login and federated logout work through `auth.skavapp.com`; immutable OIDC subjects identify product users. |
| Profile authorization | Personal maps to the Hermes default profile and Work maps to the named `work` profile. Users can hold one or both ZITADEL profile roles. |
| Shared profile conversations | Profile members can list shared PostgreSQL chats and Hermes-native sessions; there is deliberately no user-level transcript isolation inside a profile. |
| Hermes-native continuation in Skavan | Hermes sessions can be listed, read and continued from the Skavan UI through the profile-scoped Sessions API. |
| Unified Hermes session identity | Every newly created Skavan chat creates and stores one immutable Hermes session ID; subsequent turns use Hermes' Sessions API and legacy PostgreSQL-only chats remain explicitly labelled. |
| Cross-client transcript refresh | A unified Skavan chat reads its complete transcript from Hermes, so messages added from Hermes terminal/Web appear after reopening or refreshing the chat; PostgreSQL message rows recover known Skavan author labels. |
| Cross-client title synchronization | Skavan rename invokes Hermes' native session-title mutation (the same persistence primitive as terminal `/title`), while chat-list refresh mirrors terminal title and activity changes back into product metadata. |
| Swing-scan response consistency | The Work profile's `swing-fib-scan` repetitive-task list uses one compact fenced-block contract (`TASK`, `PARAMS`, `PROMPT (one-liner)`, `PROMPT`, `BEST FOR`) and the skill forbids alternative layouts. |
| User identity presentation | Registered names are synchronized into PostgreSQL and the given name is displayed in the authenticated UI. |
| Theme preference | Four approved themes are available and the selected theme is persisted in the user's PostgreSQL JSONB preferences. |
| Default profile preference | Users with two profiles can save the profile that opens by default on mobile, tablet and desktop. Single-profile users enter their only authorized profile automatically. |
| Revoked default handling | If an administrator revokes the saved default profile, Skavan selects and persists an authorized fallback; chat is disabled if no profile remains. |
| Responsive chat experience | Sticky composer/navigation, scroll controls, dynamic multiline input, content-sized bubbles, right-aligned user messages, Markdown/GFM rendering and responsive long-title headers are deployed. |
| Chat input behavior | Enter creates a newline, Send submits explicitly, and Ctrl+Enter submits on desktop. |
| Streaming resilience | The UI shows active streaming state; API SSE heartbeats prevent idle Cloudflare/mobile disconnects during long Hermes tool operations. |
| Chat management | Search, latest-activity ordering, PostgreSQL chat rename/archive controls and Hermes session discovery are available. |
| Long session history | Existing Hermes messages larger than 20,000 characters can be loaded without API validation failure. |
| Session cookies | Auth sessions use a 365-day sliding lifetime. |
| Deployment | Laptop 2 runs the web, API, Hermes, ZITADEL and reverse proxy services with Docker Compose; web, API and Hermes are healthy after the latest deployment. |
| UI design system | The approved nerdy visual system, semantic theme tokens, icons and responsive rules are recorded in `docs/architecture/ui-design-system.md`. |
| Saved-task response contract | Skavan adds an invisible Hermes instruction for repeatable-task, saved-prompt and prompt-template requests. Hermes must re-read the selected skill's template during the current run and preserve its headings and fenced blocks instead of reconstructing prose from chat memory. |
| Mobile plain-text block wrapping | Markdown fences labelled `text`, `plaintext` or `txt` wrap within the message viewport on mobile and desktop; programming-language code fences retain horizontal scrolling and tables keep their independent responsive scroller. |
| Mobile stream recovery for all chats | If a mobile browser drops a long SSE response, both platform-controlled and directly listed Hermes chats poll their authoritative saved history and replace the partial response automatically instead of leaving a raw `Load failed` error. |
| Unified-chat list deduplication | Platform chats expose their existing Hermes session binding to the web client. The merged chat list suppresses the corresponding native-session row by stable session ID while retaining genuinely separate conversations that merely share a title. |
| Profile authorization acceptance suite | Release-blocking coverage verifies Personal-only, Work-only, both profiles, revoked defaults, all roles revoked, wrong-profile denial and two-user shared profile chat visibility. |
| Live cross-client transcript refresh | Open Skavan chats poll their canonical Hermes transcript every five seconds while visible and refresh immediately when the browser tab regains focus. Identical transcripts do not trigger a React update. |
| Platform session writer guard | The single FastAPI instance serializes Skavan turns per profile/session, allows one bounded pending turn, reports queued state and applies bounded Hermes 429 backoff. The direct Hermes terminal boundary is recorded in ADR-016. |
| Hermes runtime event UX | Safe tool start/completion/failure and interruption events are normalized by the backend without exposing tool arguments; the UI displays current progress during long runs. |

## P0 — next implementation work

| Task | Definition of done |
| --- | --- |
| Direct-client writer coordination | Add or adopt a Hermes-native per-session lease (or require a shared writer wrapper) so direct terminal/Web turns and Skavan turns participate in the same mechanical lock. Skavan-side serialization is complete. |

## P1 — release and operational follow-up

| Task | Next action |
| --- | --- |
| ZITADEL proxy health | Diagnose why `zitadel-proxy` reports unhealthy while ZITADEL API/login and public authentication remain functional; correct the health check or underlying routing issue. |
| Profile backup/restore | Back up and independently restore the default Personal and named Work Hermes data directories, including their `state.db`, `USER.md` and `MEMORY.md`. |
| Shared-memory acceptance | Prove Personal and Work memory isolation and same-profile sharing using explicit test facts. |
| Off-host recovery | Select encrypted off-host backup storage, key custody, retention, alerts and recovery objectives; perform a documented restore rehearsal. |
| Deployment documentation | Update the clean-machine runbook with the pinned Docker executable discovery, current Compose command, profile bootstrap and post-deployment acceptance checks. |

## P3 — non-blocking extensions

| Task | Guardrail |
| --- | --- |
| Legacy chat importer | Keep migration explicit, idempotent and reversible; never migrate during a normal chat read. |
| Safe `/commands` support | Start with read-only help, session list/status/title and profile information. Keep terminal, filesystem, credentials, config mutation, cron and administration unavailable to normal users. |
| Optional OmniRoute provider | Evaluate provider compatibility, routing, cost, failover and secret handling behind the Hermes adapter. |
| Mechanical action ledger | A reviewed best-effort observer hook may record tools, but it does not replace authorization or turn coordination. |
| Messaging channels | Add Telegram and WhatsApp only after web/session identity is stable. |
| Mobile and voice | Reuse the same backend, profile authorization and session coordinator contracts. |

## Decisions required

1. Upstream/shared-wrapper mechanism for direct Hermes clients to participate
   in the ADR-016 per-session lease.
2. Encrypted off-host backup destination and recovery-key custodian. Initial
   targets are RPO 24 hours, RTO 4 hours, 30-day retention and quarterly restore tests.

## Known non-goals for Phase 1

- No user-level chat isolation within a Personal or Work profile.
- No Redis or Kubernetes dependency.
- No public Hermes API or Hermes API key in the browser.
- No voice, native mobile app, Telegram or WhatsApp until the web session model
  is stable.

## Task-capture rule

When implementation or testing reveals unplanned product, security, deployment
or reliability work, add it to this ledger in the same development session.
Record completed/deployed behavior under **Completed and deployed** and unfinished
work under the appropriate P0/P1/P3 section. Chat history is not the project
task system.

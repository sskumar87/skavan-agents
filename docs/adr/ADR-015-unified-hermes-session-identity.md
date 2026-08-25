# ADR-015: Unify new Skavan chats with Hermes sessions

- Status: Accepted
- Date: 2026-08-25
- Supersedes: the split-transcript decision for new chats in ADR-014

## Context

Skavan-created chats were stored in PostgreSQL and sent to Hermes through the
stateless chat-completions endpoint. Hermes terminal and dashboard clients use
Hermes sessions stored in the selected profile's `state.db`. Consequently, a
conversation created in Skavan could not be opened and continued from another
Hermes client as the same conversation.

## Decision

Every newly created Skavan chat receives one immutable Hermes session identity.
The PostgreSQL `threads.hermes_session_id` field binds the product thread to that
session. New turns use Hermes' Sessions API, so Hermes Web, the terminal, and
Skavan can continue the same runtime conversation.

PostgreSQL remains the product store for chat metadata, authorship, audit data,
and the UI transcript mirror. Hermes remains authoritative for agent runtime
context and its session transcript.

Existing threads have a null binding and remain operational through the legacy
stateless route. They will not be silently merged into a Hermes session because
doing so could create misleading or duplicated history. A separate reviewed
migration may import them later.

Skavan generates deterministic session IDs in the form
`skavan-<thread UUID>`. Creation is idempotent: an existing matching Hermes ID
is accepted. A database failure after Hermes creation can leave an unused Hermes
session whose `source` is `skavan`; this source makes reconciliation safe.

Hermes session data must be included in platform backups. Persistent storage is
not equivalent to an immutable archive: sessions can still be deleted or lost
if their Docker volume is removed.

## Consequences

- New Skavan conversations become visible and resumable across Hermes clients.
- Hermes receives only the latest user turn for a bound session; it loads prior
  context from the session itself.
- Existing PostgreSQL-only chats remain labeled legacy until explicitly migrated.
- PostgreSQL and Hermes require reconciliation and backup procedures.

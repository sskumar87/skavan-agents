# ADR-016: Canonical transcripts and extensible turn coordination

- Status: Accepted
- Date: 2026-08-26
- Extends: ADR-015

## Context

Unified chats can be continued by Skavan, Hermes Web and the Hermes terminal.
The product needs one transcript authority, an explicit policy for legacy
PostgreSQL-only chats, and protection against duplicate concurrent turns. The
Phase 1 deployment has one FastAPI process but the design must remain open to
multiple API replicas and additional clients later.

## Decision

Hermes `state.db` is the canonical transcript for every unified chat.
PostgreSQL stores product metadata, the immutable Hermes session binding,
Skavan authorship labels, audit data and legacy transcripts. Its message rows
for unified chats are a product mirror, not an independent conversation truth.

Existing PostgreSQL-only chats remain operational and clearly labelled
`legacy`. They are not bulk-migrated. A future opt-in importer may create a new
Hermes session, copy the transcript once, validate counts and hashes, then bind
the thread. Chat reads do not contain implicit migration behavior.

Chat endpoints depend on a session-turn coordinator contract. The Phase 1
implementation is process-local because one FastAPI instance is deployed. It:

- serializes writers by `<profile>:<Hermes session ID>`;
- permits one pending turn per session;
- rejects queue overflow and bounds queue wait time;
- reports queued/busy state to the UI; and
- retries Hermes global-limit HTTP 429 responses with bounded backoff.

The replacement contract for multi-process deployment is a profile-scoped
coordinator rooted under the shared Hermes runtime, conceptually:

```text
/opt/data/runtime/session-locks/<profile>/<safe-session-key>.lock
```

or an equivalent distributed lease. Session identifiers must be encoded or
hashed before becoming filenames. The coordinator implementation can change
without changing chat endpoints.

## Direct Hermes client boundary

The deployed Hermes version has a global active-session/run limit but no native
per-session writer lock shared by its Sessions API, Web UI and terminal. The
Skavan coordinator therefore mechanically protects Skavan requests today. Full
terminal-versus-Skavan exclusion requires either upstream Hermes per-session
leases or a reviewed wrapper used by every writer. Session timestamps are not
used as locks because check-then-act is race-prone.

## Consequences

- Transcript reconciliation has one unambiguous source.
- Legacy history is preserved without risky automatic conversion.
- Phase 1 avoids Redis while the coordinator remains replaceable.
- Multi-replica FastAPI deployment must replace the in-process coordinator
  before scaling beyond one writer process.
- The direct-client coordination limitation remains visible in the P0 ledger
  until Hermes or all client entry points participate in the same lease.


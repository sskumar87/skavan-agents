# ADR-014: Continue Hermes-native sessions in the product UI

**Status:** Accepted

## Context

ADR-013 makes PostgreSQL authoritative for chats created by Skavan. Operators
can also create conversations directly in the Hermes terminal. Those native
sessions live in the selected Hermes profile's `state.db` and are not visible
in PostgreSQL, so a profile member cannot currently discover or continue them
from the product UI.

The product owner requires every member of an assigned profile to list and
continue the native sessions belonging to that profile. There is deliberately
no user-level transcript isolation inside a profile.

## Decision

Skavan supports two explicitly labelled conversation sources:

- **Skavan chat**: PostgreSQL remains authoritative for transcript, title,
  authorship and audit. These chats continue through `/v1/chat/completions`.
- **Hermes terminal**: Hermes remains authoritative for transcript, title and
  continuation. These sessions are read and continued using the pinned Hermes
  Sessions API.

FastAPI performs profile authorization before every Hermes session operation.
It maps `personal` to the unprefixed default-profile routes and `work` to
`/p/work/...`. The browser may supply only one of those fixed product profile
keys and never receives a Hermes URL or API key.

The initial slice exposes read/list/continue only:

```text
GET  /api/sessions
GET  /api/sessions/{id}/messages
POST /api/sessions/{id}/chat/stream
```

Skavan normalizes these behind its own API and BFF. A terminal session is
labelled in the UI and is not silently copied into a PostgreSQL chat. Creating,
deleting, forking, pinning and renaming Hermes-native sessions remain deferred.
PostgreSQL chat titles may be renamed through the product API.

## Consequences

- A conversation started in a Hermes terminal can continue from Skavan and
  then again from Hermes because both use the same native session.
- Terminal transcripts do not have reliable Skavan user attribution; existing
  user messages are labelled `Terminal user`.
- Authorization is profile-wide. Every role holder can read and continue every
  native session in that profile.
- Backup and recovery must cover both PostgreSQL and the Hermes profile data
  directory.
- Search and product audit across Hermes-native message contents require a
  later metadata/indexing decision; the initial implementation does not create
  a second transcript authority.

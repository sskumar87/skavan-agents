# ADR-013: Personal and Work are shared Hermes profile workspaces

**Status:** Accepted

**Supersedes for V1:** ADR-002's group-centric collaboration model and the
per-user interpretation of ADR-005.

## Context

The initial architecture used product groups and per-user personal threads as
the primary collaboration and isolation boundaries. For the first release this
adds membership and memory-management overhead that is not required by the
product owner.

Hermes already provides profile-scoped configuration, `USER.md`, `MEMORY.md`,
skills, credentials, sessions and gateway multiplexing. The desired product
has two shared contexts and no user-level chat isolation.

## Decision

V1 exposes exactly two shared workspaces:

- `personal`, backed by the Hermes `personal` profile;
- `work`, backed by the Hermes `work` profile.

ZITADEL project roles define which workspaces appear in the user's JWT:
`profile.personal` and `profile.work`. Personal is the default registration
role and Work is optional. A user may hold both roles. Within an assigned
workspace every member can list every thread, create a thread and participate
in any existing thread. User identity remains attached to messages for
attribution and audit, but it is not a transcript-isolation boundary.

The UI offers only profiles present in the validated JWT roles claim. A browser
selection changes the active context but cannot grant a role. FastAPI refreshes
its internal role mirror only from a signature-, issuer-, audience- and
expiry-validated ZITADEL token. Client preferences and request bodies are never
authorization sources.

Registration is the only self-service enrollment point: Personal is always
assigned and the user may request Work. The backend converts that fixed request
into a ZITADEL role assignment using a least-privilege service identity, then
forces a fresh login. Access begins only after the new role is present in the
refreshed JWT.

FastAPI owns the allowlist and maps workspace keys to Hermes gateway routes:

```text
personal -> /p/personal/v1/chat/completions
work     -> /p/work/v1/chat/completions
```

The browser sends only the product workspace key. It cannot provide a Hermes
URL or arbitrary profile name. FastAPI rejects any value outside the fixed
allowlist.

PostgreSQL remains authoritative for users, threads, messages and message
authors. Hermes owns profile memory. `USER.md` and `MEMORY.md` are deliberately
shared by all users of the corresponding workspace. If an external memory
provider is enabled later, its session key is workspace-scoped rather than
user-scoped.

Existing per-user histories are legacy private data. They are not exposed or
migrated into either shared workspace automatically.

## Consequences

- “Personal” means the shared Personal profile, not a private user area.
- Every member of a workspace can read information placed in that workspace.
- Product groups, group roles and group-memory retrieval are not part of the
  active V1 user experience, although their schema may remain for a future
  authorization model.
- Removing or restricting access by user will require a future authorization
  decision and migration.
- Profile creation, gateway multiplexing and profile-level backups become
  required deployment steps.

# ADR-017: Telegram identity and profile routing

## Status

Accepted — 2026-08-26

## Context

Hermes has a native Telegram Gateway with profile-scoped bot credentials,
pairing, streaming replies, media and commands. Skavan, not Hermes, owns product
users and the Personal/Work authorization decision. Enabling a public bot with
an unrestricted allowlist would bypass that boundary.

## Decision

- Use the upstream Hermes Telegram Gateway; do not fork its adapter.
- Configure Telegram independently for the Hermes default profile (product
  Personal) and named `work` profile. Each active profile uses its own bot token.
- Keep bot tokens in each profile's external Hermes `.env`; never store them in
  PostgreSQL, source control, browser storage or a Skavan response.
- Keep `TELEGRAM_ALLOW_ALL_USERS` disabled. Unknown direct-message users receive
  Hermes' short-lived pairing code but cannot run the agent until approved.
- The user approves that code while authenticated in Skavan. The backend first
  verifies the requested profile is present in current product authorization,
  then calls the private password-protected Hermes pairing API.
- Store the canonical Telegram user ID in `channel_identities` and normalized
  profile grants in `channel_identity_profiles`. A Telegram identity can be
  linked to only one product user and may hold one or both profile grants.
- Removing a connection revokes Hermes before deleting the product grant. Role
  reconciliation must revoke a messaging grant when its ZITADEL profile role is
  removed; until that automated reconciliation ships, Telegram activation is a
  controlled pilot rather than general availability.
- Telegram conversations remain Hermes-native sessions in the selected profile.
  The existing Sessions API makes them discoverable and continuable in Skavan.

## Consequences

This preserves upstream Telegram features and the existing shared-profile
memory model. Two bots make the profile boundary visible and avoid ambiguous
per-message routing. The private dashboard API becomes an internal dependency
of the Skavan backend for link and unlink operations; it remains unreachable
from the browser and public reverse proxy.

The design extends to WhatsApp and other gateways by reusing
`channel_identities` plus profile grants while keeping provider-specific
credentials and enrollment adapters separate.

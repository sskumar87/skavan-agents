# Telegram pilot runbook

This runbook activates the upstream Hermes Telegram Gateway without exposing a
bot token or granting anonymous users agent access.

## Prerequisites

- The Phase 1 stack is healthy and database migration `20260826_0003` is applied.
- `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` and
  `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD` exist in the external Phase 1 `.env`.
- Create a bot with Telegram `@BotFather`. Create a second bot only when both
  Personal and Work will be piloted; Hermes credentials are profile-scoped.
- Decide which profile is piloted first. Work is recommended so the boundary is
  explicit during acceptance testing.

## Configure Hermes

1. Open the Hermes dashboard from Laptop 2's trusted local/VPN path.
2. Select the target profile. `default` maps to Personal; `work` maps to Work.
3. Open **Channels**, choose Telegram and enter that profile's BotFather token.
4. Leave **allow all users** off. Use pairing for unknown direct messages.
5. Enable Telegram and restart the Hermes gateway when prompted.
6. Confirm the Telegram platform reports connected for the selected profile.

The dashboard saves the token into the selected profile's external `.env` and
the enablement flag under `platforms.telegram.enabled`. Do not add either token
to the repository `.env` examples or Compose YAML.

## Link a product user

1. The user sends a direct message to the profile's bot.
2. Hermes returns an eight-character, short-lived pairing code.
3. While logged into Skavan, the user opens **Connections → Telegram**, selects
   an authorized profile and enters the code.
4. Skavan verifies profile access, approves the code over the private Docker
   network and stores the Telegram identity/profile grant in PostgreSQL.
5. The user sends a new message to the bot and confirms a Hermes reply.
6. Confirm the resulting Telegram session appears in the same profile's Skavan
   chat list and can be continued from the web client.

## Acceptance and rollback

- An unpaired Telegram account must not invoke tools or receive an agent answer.
- A user without the selected profile must receive a profile-access denial.
- The same Telegram account cannot link to two different Skavan users.
- Unlinking must remove the Hermes pairing before deleting the database grant.
- No token, pairing code or dashboard password may appear in application logs.

For rollback, disable Telegram for the affected profile in Hermes Channels,
restart the gateway, then revoke pilot users. Keep the database migration; it is
additive and reusable by future messaging providers.

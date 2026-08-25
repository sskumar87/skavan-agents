# Clean-machine deployment runbook

This is the required release procedure for new machines. Follow it in order; do not substitute unreviewed images, public database access, browser-held secrets, or guessed ZITADEL/Hermes configuration.

## 1. Target topology

| Machine | Runs | Exposure |
| --- | --- | --- |
| Laptop 1 | Docker-hosted PostgreSQL + pgvector, ZITADEL database, backups | Private network only |
| Laptop 2 | Cloudflare Tunnel, reverse proxy, web, API, ZITADEL and Hermes | Tunnel is the only public ingress |

The browser path is `Cloudflare → Tunnel → private Docker reverse proxy → web/API`. The API alone calls Hermes. Hermes Dashboard is for trusted operators over private network/VPN; it is never a normal-user route. Redis and Kubernetes are not V1 requirements.

## 2. Prerequisites and decisions

Record before installation:

1. Stable private networking, reserved addresses/internal DNS, firewall authority and time sync for both laptops.
2. Cloudflare account/domain, Tunnel authority and final public hostnames for app and OIDC issuer.
3. Docker Engine + Compose on both laptops, a supported PostgreSQL + pgvector container image, and a separate encrypted backup destination.
4. Chosen, pinned, supported ZITADEL and Hermes releases; review their vendor instructions before enabling their profiles.
5. Operational owner, monitoring destination, recovery objectives, maintenance window and trusted operator access method.

## 3. Secrets

Create a protected deployment-only secret store and ignored root `.env` on Laptop 2. Never commit, log, screenshot or expose these values in browser code.

- separate product and ZITADEL database credentials;
- database TLS material;
- ZITADEL bootstrap, session, OIDC-client and SMTP secrets;
- Hermes API server key;
- Cloudflare Tunnel credential/token;
- approved hostnames/origins; and
- backup encryption/storage credentials.

Assign an owner and rotation date to every secret. Only API receives the Hermes key.

## 4. Prepare Laptop 1

1. Patch the OS; enable time sync, encrypted storage and restricted administration.
2. Install Docker Engine + Compose and run PostgreSQL + pgvector as a dedicated container with durable encrypted host storage. Create separate product/ZITADEL databases and non-superuser roles.
3. Bind the database container only to Laptop 1's private interface; permit only Laptop 2's private address, require TLS and never expose/forward port 5432.
4. Use the database superuser to enable `vector` once per target database. Create a separate migration role for schema changes and a restricted API runtime role; do not give the runtime role extension or schema-creation privileges.
5. Test authenticated TLS connections from Laptop 2.
6. Configure encrypted backups plus WAL/PITR to a location outside Laptop 1. Prove a restore before accepting production data.
7. Run `infra/laptop1/preflight.sh`; resolve every failure and record its warnings in the deployment record.

## 5. Prepare Laptop 2

1. Patch/harden the OS; enable time sync/encrypted storage; install Docker Engine + Compose from trusted sources.
2. Obtain a tagged, reviewed release. Copy `infra/docker/compose.laptop2.example.yml` to ignored `compose.laptop2.yml` and `.env.example` to ignored `.env`.
3. Supply verified deployment values only. Confirm the reverse proxy has no host-published port, no database container exists, and API alone gets the Hermes key.
4. Start from the reviewed references in `image-inventory.md`. Re-resolve and review digests during an intentional upgrade, then record the deployed image IDs in the release record.
5. Run `powershell -ExecutionPolicy Bypass -File infra/laptop2/preflight.ps1`; do not deploy while it reports failures.

## 6. Identity and Hermes gates

For ZITADEL, follow official instructions for the selected release. Verify bootstrap/recovery, public issuer URL, OIDC apps, PKCE redirects/logout URLs, scopes, signing-key rotation and email delivery. Map immutable OIDC `sub` to the product user; proxy only approved public OIDC routes.

For Hermes, verify the exact release's private API binding, persistent state, profiles, streaming API, server key, gateway setup, upgrades and Dashboard restrictions. The product API is the only normal product caller. Keep Telegram/WhatsApp disabled until their identity-linking flow has been delivered and tested.

## 7. Configure Cloudflare Tunnel

1. Create a named, least-privilege Tunnel; store credentials outside the repo.
2. Map the approved app hostname to `reverse-proxy:8080` and the OIDC hostname to `zitadel-proxy:80` on Laptop 2's private Docker network.
3. Never map Hermes, Dashboard, PostgreSQL, Docker or admin endpoints.
4. Install the connector with a restart policy; configure Access/WAF/rate limits as needed.
5. Verify externally that only intended routes are reachable and no laptop port is public.

## 8. Release and migration order

1. Record release SHA and take a verified Laptop 1 backup.
2. Validate private PostgreSQL reachability and review current/target Alembic revisions.
3. Start reverse proxy, web and API; enable verified ZITADEL/Hermes only after their gates are complete.
4. Using the database superuser, enable `vector` once in the target database if it is not already installed. Configure Laptop 2 with `infra/laptop2/configure-product-database.ps1`; it saves `skavan_app` as `DATABASE_URL` and the table-owning `skavan_migrator` as `SKAVAN_MIGRATION_DATABASE_URL`. Run `infra/laptop2/run-product-migrations.ps1` for every deployment that includes a revision. The wrapper refuses the runtime account. Apply forward only; record the resulting revision. Never autogenerate or casually downgrade production schema.
5. Complete ZITADEL client configuration, restart affected services, then enable Tunnel traffic.

## 9. Acceptance checklist

- DNS, public TLS and OIDC discovery work; Tunnel reconnects after restart.
- Login uses Code + PKCE; no browser request has a Hermes key or direct Hermes endpoint.
- A user can create group/thread, receive Hermes stream and find persisted history.
- Same-group memory recall works; cross-group and removed-member recall are denied before vector search.
- Dashboard/PostgreSQL are unreachable from public and normal-user paths.
- Backup/monitoring jobs are healthy; image digests and Alembic revision are recorded.

## 10. Operations, recovery and rollback

Upgrade in a maintenance window: backup, verify restore point, deploy approved release, review migrations, migrate forward, restart, run acceptance checks and monitor logs. For an app regression, remove Tunnel traffic/enable maintenance and redeploy a compatible earlier app release—do not automatically roll back schema. For migration failure, preserve logs and choose a forward fix or tested restore plan.

Test restore at least quarterly and before major upgrades in an isolated environment. Maintain a deployment record with release SHA, images, Alembic revision, backup ID, ZITADEL/Hermes versions, Tunnel ID, operators, acceptance results and rollback point.

## 11. Troubleshooting

| Symptom | First checks |
| --- | --- |
| Tunnel unavailable | connector service, credential, DNS and localhost proxy; never expose a port to diagnose |
| 502/503 | proxy-to-web/API networking, container health/logs, release image and bindings |
| OIDC loop | issuer, forwarded headers, PKCE redirects, cookies and time sync; do not weaken validation |
| Database failure | Laptop 1 reachability, firewall, TLS, credentials/roles; never make DB public |
| Hermes unavailable | API private endpoint/key/profile health; return safe product error, no browser-direct fallback |
| Memory anomaly | stop access, inspect membership query/audit events; treat cross-group exposure as incident |

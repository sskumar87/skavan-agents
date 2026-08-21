# ZITADEL

Self-hosted ZITADEL is the OIDC/OAuth2 identity provider. This platform maps
the immutable OIDC `sub` to its own user record and evaluates product
authorization locally.

## Phase 1 login

The minimal Laptop 2 flow uses the existing Laptop 1 PostgreSQL server and does
not start another PostgreSQL container. For local-only bootstrap, use
`http://auth.localhost:8081` and `http://localhost:8080`. For a Cloudflare
Tunnel deployment, configure the final HTTPS application and identity
hostnames before restarting the identity profile.

Before starting the `identity` profile:

1. Run `infra/zitadel/configure-phase1-login.ps1`. Its defaults are the public
   Phase 1 hosts `https://skavan.skavapp.com` and
   `https://auth.skavapp.com`; pass `-AppOrigin` and `-ZitadelIssuerUrl`
   explicitly only when preparing a different deployment. It prompts for the new
   database-role password and initial administrator password, generates all
   other keys, updates the protected external `.env`, and writes
   `zitadel-create.sql` beside it without displaying secrets.
2. Run that generated SQL through the existing IntelliJ administrative
   connection. It creates the dedicated role when missing or rotates its
   password when it exists, then confirms ownership of the existing `zitadel`
   database. On a completely clean PostgreSQL server, create the `zitadel`
   database once before running the generated SQL.
3. Keep the generated `.env`, master key, and SQL file outside the repository;
   back up the master key because it cannot be changed after initialization.
4. Start `docker compose --env-file <protected-env> -f
   infra/docker/compose.phase1.yml --profile identity up -d --wait`.
5. Open the ZITADEL console and create a project plus a Web OIDC application
   using Authorization Code + PKCE. Authentication Method must be `None`.
6. Register exact callback and logout URIs for the selected origin. For the
   public Skavan deployment these are
   `https://skavan.skavapp.com/auth/callback/zitadel` and
   `https://skavan.skavapp.com/login`.
7. Put the generated client ID in `ZITADEL_CLIENT_ID` in the protected `.env`,
   then rebuild the web service. The setup script has already generated the
   remaining authentication values. PKCE clients do not use a client secret.

The local HTTP configuration is strictly a Laptop 2 bootstrap mode. Cloudflare
deployment uses a final `https://auth.<domain>` issuer and exact HTTPS callback
URLs; do not enable ZITADEL development mode there. Set `APP_ORIGIN`,
`ZITADEL_DOMAIN`, `ZITADEL_ISSUER_URL`, `ZITADEL_EXTERNAL_PORT`,
`ZITADEL_EXTERNAL_SECURE`, and `ZITADEL_EXTERNAL_SCHEME` in the protected
environment file before recreating the web and identity services.
The setup script updates deployment files only. ZITADEL applies
`FIRSTINSTANCE` and `DEFAULTINSTANCE` values when an instance is first created;
for an existing instance, update **Default Settings > Features > Login V2** in
the Console (or use the Feature API) and set its base URI to the final public
issuer plus `/ui/v2/login`.

## Reusable E2E user

Run `infra/zitadel/prepare-e2e-user.ps1` to generate the dedicated non-admin
`codex-e2e` test credential outside the repository. By default it writes
`C:\SKAV_PLATFORM\secrets\skavan-phase1\test-users\codex-e2e.json`, reuses an
existing file, and never prints the password. Create the corresponding ZITADEL
user with its e-mail marked verified and do not assign administrator roles.
Use this identity only for repeatable product login, user synchronization, and
chat persistence tests.

The Laptop 2 Compose template follows ZITADEL v4.17.1's production-like
lifecycle: `zitadel-init`, `zitadel-setup`, `zitadel-api`, `zitadel-login`, and
an HTTP/2-capable Traefik proxy. ZITADEL's PostgreSQL database remains on
Laptop 1; the template does not start another PostgreSQL container.

## Required deployment values

Create an ignored root `.env` and supply:

- `ZITADEL_DOMAIN`: the public identity hostname, normally `auth.<domain>`;
- `ZITADEL_MASTERKEY_FILE`: path to a protected file containing exactly 32
  securely generated characters, backed up before first initialization because
  the key cannot be changed casually;
- `ZITADEL_DATABASE_POSTGRES_DSN`: the dedicated Laptop 1 `zitadel` database
  and non-superuser owner credential;
- `LOGIN_CLIENT_PAT_EXPIRATION`: a reviewed bootstrap-token expiry; and
- the immutable image references from `docs/deployment/image-inventory.md`.

Use `sslmode=verify-full` with a mounted CA in the final database DSN. The
example temporarily shows `sslmode=require` because Laptop 1 database TLS
certificate provisioning is still pending. Compose mounts the master-key file
read-only and ZITADEL reads it with `--masterkeyFile`, keeping the key out of
container command metadata. Never put the DSN or master key in Git,
screenshots, browser code, or chat.

## Bootstrap order

1. Confirm the dedicated `zitadel` database/role exists on Laptop 1 and is
   reachable only over the private network.
2. Set the final `auth.<domain>` in `.env` and in the protected Cloudflare
   Tunnel config before first initialization.
3. Start the identity profile with the ignored deployment Compose file.
4. Confirm `zitadel-init` and `zitadel-setup` complete successfully, and that
   `zitadel-api`, `zitadel-login`, and `zitadel-proxy` are healthy.
5. Verify `https://auth.<domain>/.well-known/openid-configuration` and the
   issuer value before creating the product OIDC application.
6. Create the web OIDC application with Authorization Code + PKCE, exact
   callback/logout URLs and no wildcard redirects. Record its client ID in the
   protected deployment environment.

The Traefik Docker socket mount follows the vendor Compose topology and is
read-only at the filesystem level. Treat it as privileged infrastructure:
never publish the Traefik dashboard, keep the proxy on the private Docker
network, and consider a restricted Docker socket proxy during hardening.

Apply Cloudflare Access restrictions to operator/management paths while
leaving required OIDC discovery, authorization, token, login and logout flows
reachable to product users.

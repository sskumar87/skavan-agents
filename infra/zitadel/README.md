# ZITADEL

Self-hosted ZITADEL is the OIDC/OAuth2 identity provider. This platform maps
the immutable OIDC `sub` to its own user record and evaluates product
authorization locally.

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

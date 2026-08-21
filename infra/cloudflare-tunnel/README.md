# Cloudflare Tunnel (Laptop 2)

Cloudflare Tunnel is the sole public ingress for V1. `cloudflared` establishes
an outbound connection from Laptop 2 to Cloudflare; no inbound router port
forwarding is required for the application.

## Boundary

`cloudflared` may reach **only** the `reverse-proxy` container. The proxy
publishes the web application and platform API (`/api/`). Hermes API, Gateway,
and Dashboard do not have public hostnames or proxy routes.

Do not configure a tunnel ingress rule directly to `hermes`, `zitadel`, or a
database. Operator access to Hermes Dashboard remains via a trusted private
network or VPN.

## One-time Cloudflare setup

1. In Cloudflare Zero Trust, create a named tunnel for Laptop 2.
2. Create a public hostname such as `app.example.com` and map it to the tunnel.
3. Store the tunnel credential JSON outside this repository, for example
   `C:\\SKAV_PLATFORM\\secrets\\cloudflared\\<tunnel-uuid>.json`.
4. Copy `config.yml.example` to that protected directory as `config.yml`, set
   the tunnel UUID and credential file name, and restrict its access.
5. Point the tunnel to `http://reverse-proxy:8080` only.

Never commit a tunnel token, credential JSON, Cloudflare origin certificate, or
a populated `config.yml`.

## Run

From the repository root, create the ignored `.env` with the external secret
location and a reviewed, pinned connector image:

```text
CLOUDFLARED_CONFIG_DIR=C:/SKAV_PLATFORM/secrets/cloudflared
CLOUDFLARED_IMAGE=cloudflare/cloudflared:<reviewed-version>
```

Then start the ingress profile together with application services:

```text
docker compose -f infra/docker/compose.laptop2.yml up -d
```

Check the connection with
`docker compose -f infra/docker/compose.laptop2.yml logs -f cloudflared`.

The proxy has no published host port: `cloudflared` reaches it through the
private Docker `edge` network. Public OIDC routing is added only after the
selected ZITADEL release and hostname are verified; do not route an unreviewed
identity service through this configuration.

## Operational checks

- Confirm no inbound firewall/router rule exposes Docker, Hermes, ZITADEL,
  PostgreSQL, or port 8080 directly.
- Confirm the public hostname serves the web application and `/api/` reaches
  the platform API when it exists.
- Confirm guessed Hermes paths return an application 404, never Hermes.
- Rotate/revoke the tunnel credential if Laptop 2 or its secrets directory is
  compromised.

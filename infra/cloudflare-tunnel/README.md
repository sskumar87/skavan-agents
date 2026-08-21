# Cloudflare Tunnel (Laptop 2)

Cloudflare Tunnel is the sole public ingress for V1. `cloudflared` establishes
an outbound connection from Laptop 2 to Cloudflare; no inbound router port
forwarding is required for the application.

## Boundary

`cloudflared` may reach only two reviewed HTTP entry points on the private
`edge` network: `reverse-proxy` for the product application/API and
`zitadel-proxy` for the dedicated identity hostname. Hermes API, Gateway,
Dashboard, PostgreSQL and Docker management do not have public hostnames.

Do not configure a tunnel rule directly to Hermes, `zitadel-api`,
`zitadel-login`, PostgreSQL, or Docker. Operator access to Hermes Dashboard
remains via a trusted private network or VPN.

## One-time Cloudflare setup

1. In Cloudflare Zero Trust, create a named tunnel for Laptop 2.
2. Create public hostnames for the application (`app.example.com`) and OIDC
   issuer (`auth.example.com`) and map both to the same named tunnel.
3. Store the tunnel credential JSON outside this repository, for example
   `C:\\SKAV_PLATFORM\\secrets\\cloudflared\\<tunnel-uuid>.json`.
4. Copy `config.yml.example` to that protected directory as `config.yml`, set
   the tunnel UUID and credential file name, and restrict its access.
5. Point the app hostname to `http://reverse-proxy:8080` and the auth hostname
   to `http://zitadel-proxy:80`. Keep the terminal 404 ingress rule.

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
docker compose --profile identity -f infra/docker/compose.laptop2.yml up -d
```

Check the connection with
`docker compose -f infra/docker/compose.laptop2.yml logs -f cloudflared`.

Neither proxy has a published host port: `cloudflared` reaches them through the
private Docker `edge` network. The command enables the reviewed ZITADEL
identity profile because the configured auth ingress requires that target.

## Operational checks

- Confirm no inbound firewall/router rule exposes Docker, Hermes, ZITADEL,
  PostgreSQL, or port 8080 directly.
- Confirm the public hostname serves the web application and `/api/` reaches
  the platform API when it exists.
- Confirm the auth hostname's discovery document reports the exact public
  HTTPS issuer and that management paths follow the approved Access policy.
- Confirm guessed Hermes paths return an application 404, never Hermes.
- Rotate/revoke the tunnel credential if Laptop 2 or its secrets directory is
  compromised.

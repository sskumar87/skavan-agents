# Laptop 2 Docker Compose topology

`compose.laptop2.example.yml` is the V1 topology template for Laptop 2. It is a
small, private service deployment—not Kubernetes and not a database provisioner.

## Boundaries

```text
Internet -> Cloudflare Tunnel -> product reverse proxy -> web / API
                              `-> ZITADEL proxy -> OIDC API / Login

API -> private-services -> Hermes API/runtime/gateway
Hermes -> service-egress -> approved cloud model/providers

Laptop 1 private network <- API and ZITADEL -> PostgreSQL + pgvector
```

- PostgreSQL and pgvector remain on Laptop 1. Compose deliberately has no
  PostgreSQL service and no published database port.
- The browser reaches only the product and ZITADEL proxy routes. It never
  reaches Hermes or uses a Hermes server key.
- Hermes API, Gateway, Dashboard, and any agent tool access remain on the
  `private-services` network. The Dashboard must be separately restricted to
  trusted operators/VPN and is not proxied here.
- Cloudflare Tunnel credentials are installed and managed on Laptop 2 outside
  this repository. Do not place tunnel tokens in Compose files or Git.

## Local deployment preparation

1. Copy the template to `compose.laptop2.yml`; do not commit that file.
2. Create the ignored root `.env` from `.env.example` and add deployment-only
   values and secrets through the chosen secret-management process.
3. Confirm Laptop 2 can privately reach Laptop 1 PostgreSQL using TLS and a
   least-privilege database account.
4. Review the immutable image inventory. The `identity` and `hermes` profiles
   remain opt-in until their secrets and bootstrap configuration are complete.
5. Configure Cloudflare Tunnel's app hostname for `reverse-proxy:8080` and auth
   hostname for `zitadel-proxy:80` on the private `edge` network.

## Deliberate TODOs

The final public hostnames, Laptop 1 database TLS/CA configuration, OIDC client
registration, Hermes model-provider credentials and Gateway channel setup are
deployment inputs. Telegram/WhatsApp and the Hermes Dashboard remain disabled
until their authorization and trusted-access work is delivered.

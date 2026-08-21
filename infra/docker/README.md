# Laptop 2 Docker Compose topology

`compose.laptop2.example.yml` is the V1 topology template for Laptop 2. It is a
small, private service deployment—not Kubernetes and not a database provisioner.

## Boundaries

```text
Internet -> Cloudflare Tunnel -> reverse proxy (127.0.0.1 only)
                                  |-> web
                                  |-> API -> Hermes API/runtime/gateway
                                  |-> ZITADEL public OIDC endpoints

Laptop 1 private network <- API and ZITADEL -> PostgreSQL + pgvector
```

- PostgreSQL and pgvector remain on Laptop 1. Compose deliberately has no
  PostgreSQL service and no published database port.
- The browser reaches only the reverse-proxy routes. It never reaches Hermes or
  uses a Hermes server key.
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
4. Pin and verify the selected ZITADEL and Hermes images/configuration. The
   `identity` and `hermes` profiles intentionally cannot start until this work
   is complete.
5. Configure Cloudflare Tunnel to forward to `http://127.0.0.1:<port>` only.

## Deliberate TODOs

The exact supported ZITADEL bootstrap/configuration, Hermes image/command,
Hermes Gateway channel configuration, and production TLS/trusted-proxy settings
depend on their verified upstream documentation and the deployment's private
hostnames. They must be added as reviewed configuration, never guessed here.

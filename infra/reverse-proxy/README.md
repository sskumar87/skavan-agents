# Reverse proxy

The reverse proxy is the private origin for Cloudflare Tunnel. It accepts
traffic only from the `cloudflared` container and routes these public product
surfaces:

- `/` to the Next.js web application;
- `/api/` to the FastAPI platform API.

Its template is [`nginx.conf.example`](nginx.conf.example). It deliberately
contains no upstream or location for Hermes API, Hermes Dashboard, Hermes
Gateway, ZITADEL administration, or PostgreSQL. Do not add an administrative
route as a convenience shortcut; use trusted-network/VPN access instead.

The proxy has no host `ports` mapping in production. See the
[Cloudflare Tunnel runbook](../cloudflare-tunnel/README.md) for deployment and
verification steps.

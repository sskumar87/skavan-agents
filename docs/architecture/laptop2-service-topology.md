# Laptop 2 service topology

## Purpose

Laptop 2 runs the product-facing services and the private Hermes runtime
boundary. Laptop 1 remains the private Docker-hosted PostgreSQL + pgvector data node.

## Service responsibility and exposure

| Service | Responsibility | Exposure |
| --- | --- | --- |
| Cloudflare Tunnel | Outbound-only public ingress | Tunnel provider to local reverse proxy |
| Reverse proxy | Single browser/API/OIDC entry point | Private Docker network only; no host port |
| Web | Next.js user interface | Reverse proxy only |
| API | Product authorization, data access, Hermes adapter | Reverse proxy and private services only |
| ZITADEL | OIDC/OAuth identity provider | Explicit public OIDC routes via proxy only |
| Hermes runtime/API/Gateway | Agent execution and channel integration | API/private operator network only |
| Hermes Dashboard | Operator administration | Trusted network/VPN only; never normal UI |
| PostgreSQL + pgvector (Laptop 1) | Product/ZITADEL data and memory vectors | Private network only |

## Required request paths

1. User traffic arrives through Cloudflare Tunnel to the localhost-bound reverse proxy.
2. Browser calls the web application and product API only through that proxy.
3. API validates identity and product authorization before retrieving data or
   calling Hermes.
4. API uses private network access to Laptop 1 PostgreSQL and Hermes.
5. Hermes responses/events return through API; no browser-to-Hermes path exists.

## Operational controls

- Use explicit allow-lists/firewall rules between Laptop 2 and Laptop 1 rather
  than relying on Docker network names alone.
- Use TLS for PostgreSQL in transit and unique least-privilege accounts for
  product and ZITADEL databases.
- Keep secrets in an ignored deployment store/.env or a future secret manager;
  do not commit `.env`, tunnel credentials, OIDC bootstrap secrets, database
  passwords, or Hermes server keys.
- Pin container versions after compatibility verification. Review upstream
  ZITADEL and Hermes deployment instructions before enabling them.
- Restrict the Hermes Dashboard and administrative endpoints using VPN/trusted
  network policy plus explicit authentication.

## Out of scope for this scaffold

This does not provision Laptop 1, configure Cloudflare Tunnel, initialise
ZITADEL, choose Hermes images, set up messaging channels, or expose the
Dashboard. Those are distinct reviewed implementation tasks.

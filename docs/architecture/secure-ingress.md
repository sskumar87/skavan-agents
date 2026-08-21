# Secure public ingress

Cloudflare Tunnel is the V1 public boundary. Laptop 2 makes an outbound tunnel
connection to Cloudflare. Cloudflare delivers traffic across that connection to
two reviewed proxies on the Docker `edge` network: the product reverse proxy
and ZITADEL's HTTP/2-capable proxy. The network has no host-published ports.

```text
Browser --> HTTPS --> Cloudflare --> outbound tunnel --> cloudflared
                                                    |-> reverse proxy --> web / API
                                                    `-> ZITADEL proxy --> OIDC / login
```

The browser has no route to Hermes, PostgreSQL or Docker. ZITADEL's public OIDC
and login paths use a dedicated hostname; operator/management paths require an
additional Cloudflare Access policy. The product reverse proxy has no route to
Hermes. The FastAPI backend alone calls Hermes using server-held credentials
on a private network.

## Public and private surfaces

| Surface | Public route | Access model |
| --- | --- | --- |
| Web application | `/` | Product authentication and authorization |
| Platform API | `/api/` | Product authentication and authorization |
| ZITADEL OIDC/login | Dedicated `auth.<domain>` hostname | Public protocol paths; ZITADEL authentication |
| Hermes API, Gateway, Dashboard | None | Internal network; dashboard also trusted network/VPN |
| ZITADEL management paths | Auth hostname with Access restriction | Trusted operators only |
| PostgreSQL + pgvector | None | Private Laptop 1 network only |

Tunnel credentials are host secrets, never repository configuration. Rotate the
credential after compromise and use Cloudflare access controls/WAF as defense in
depth; they do not replace platform authorization.

# Secure public ingress

Cloudflare Tunnel is the V1 public boundary. Laptop 2 makes an outbound tunnel
connection to Cloudflare. Cloudflare delivers traffic across that connection to
the reverse proxy on the Docker `edge` network. That network allows outbound
Cloudflare connectivity for `cloudflared`, but has no host-published ports.

```text
Browser --> HTTPS --> Cloudflare --> outbound tunnel --> cloudflared
                                                    --> reverse proxy --> web / API
```

The browser has no route to Hermes, PostgreSQL, Docker, or the identity-provider
administration surface. The reverse proxy has no route to Hermes. The FastAPI
backend alone calls Hermes using server-held credentials on a private network.

## Public and private surfaces

| Surface | Public route | Access model |
| --- | --- | --- |
| Web application | `/` | Product authentication and authorization |
| Platform API | `/api/` | Product authentication and authorization |
| Hermes API, Gateway, Dashboard | None | Internal network; dashboard also trusted network/VPN |
| ZITADEL administration | None | Trusted operator network only |
| PostgreSQL + pgvector | None | Private Laptop 1 network only |

Tunnel credentials are host secrets, never repository configuration. Rotate the
credential after compromise and use Cloudflare access controls/WAF as defense in
depth; they do not replace platform authorization.

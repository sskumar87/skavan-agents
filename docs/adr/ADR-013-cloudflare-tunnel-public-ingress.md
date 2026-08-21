# ADR-013: Cloudflare Tunnel for public ingress

**Status:** Accepted

Laptop 2 will use Cloudflare Tunnel as the public ingress path. The connector makes outbound connections to Cloudflare and forwards only approved HTTPS application routes to the reverse proxy, so the platform does not require inbound public ports.

The tunnel does not alter product authorization: ZITADEL remains the identity provider and FastAPI remains the policy enforcement point. Hermes APIs, credentials and the operator dashboard stay private. Tunnel tokens and Cloudflare credentials are deployment secrets and are not committed to this repository.

# Container image inventory

This inventory records the reviewed image set used by the Laptop 2 example on
2026-08-21. Tags make the release human-readable; digests make pulls immutable.
Do not replace these values with `latest` in a deployment environment.

| Purpose | Immutable image reference |
| --- | --- |
| Web build/runtime | `node:24.19.0-alpine3.24@sha256:d32cdf619f63fe0471182d08996dd516c6275bb5fd31ae06e55a570bd9e1ad43` |
| API build/runtime | `python:3.13.14-slim-bookworm@sha256:67a1e1f215ccda113cfc024e8639049257e88f273898f595b61476d128d387e8` |
| Reverse proxy | `nginx:stable-alpine@sha256:97d490c12ba55b4946b01546d1c3ed324e8d41ab1c9fcb2a616aa470620e5b46` |
| Tunnel connector | `cloudflare/cloudflared:2026.7.3@sha256:e39ee8da81ad5e05d77f38d2f51c60ca51bf2a8450ac3abab50c17fdb91d91bf` |
| Identity provider | `ghcr.io/zitadel/zitadel:v4.17.1@sha256:3ac6910685d48f32481f01f45e3e6215efe5a9df2c069591b481e9a101712db5` |
| Identity login UI | `ghcr.io/zitadel/zitadel-login:v4.17.1@sha256:8035df2409afb35a3999482ee98e453261715f98d47e4b62e948e4a1ddf4345f` |
| Identity HTTP/2 proxy | `traefik:v3.7.7@sha256:1cb3845d7a05e1473c9086351426597e911db49db382b6e4769f9b0744962ac8` |
| Agent runtime | `nousresearch/hermes-agent:v2026.8.18@sha256:22e37bb4ed1b0f50cb6bd991dca7ecacd6c9f29df9b4a20fc989d32bc763ccf6` |

The Node image follows the current LTS line. Newer non-LTS Node releases are
not adopted merely because they have a higher version number. Application
packages use their latest stable releases and are locked separately by npm and
uv.

## Update procedure

1. Review upstream release notes and security advisories.
2. Resolve the new multi-platform index digest from the publisher registry.
3. Update this inventory, `.env.example`, and Dockerfile defaults together.
4. Rebuild from clean lockfiles and run API, web, Compose and acceptance tests.
5. Deploy one reviewed release and record its actual image IDs in the
   deployment record. Do not allow unattended production image updates.

Upstream references:

- https://hub.docker.com/_/node
- https://hub.docker.com/_/python
- https://hub.docker.com/_/nginx
- https://github.com/cloudflare/cloudflared/releases
- https://github.com/zitadel/zitadel/releases
- https://github.com/NousResearch/hermes-agent/releases

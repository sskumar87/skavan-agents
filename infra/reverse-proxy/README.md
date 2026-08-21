# Reverse proxy

Cloudflare Tunnel forwards approved public HTTPS application routes to this component from Laptop 2. No inbound ports need be opened for the application.

Hermes API and dashboard routes remain private; the dashboard is limited to trusted operators. Tunnel credentials are deployment secrets and must never be committed.

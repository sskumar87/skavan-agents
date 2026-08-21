# API service

FastAPI modular monolith. Planned modules are `auth`, `users`, `groups`, `conversations`, `memory`, `permissions`, `hermes_adapter`, `approvals`, and `audit`.

The API is the only product component allowed to call Hermes.

## Phase 1 routes

- `GET /healthz` — API readiness.
- `GET /api/hermes/health` — server-side Hermes reachability.
- `POST /api/chat/stream` — normalized SSE stream for the custom UI. Emits
  `token`, `done`, and user-safe `error` events; Hermes-specific events and
  credentials never reach the browser.
- `POST /api/chat` — temporary non-streaming compatibility route.

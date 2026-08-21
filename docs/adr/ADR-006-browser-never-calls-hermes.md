# ADR-006: Browser never calls Hermes directly

**Status:** Accepted

The FastAPI backend is the exclusive Hermes client. It resolves context, limits capabilities, streams events and keeps API credentials server-side.

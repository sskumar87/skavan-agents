from fastapi import FastAPI


app = FastAPI(title="Skavan Agents API", version="0.1.0")


@app.get("/healthz", tags=["system"])
async def health_check() -> dict[str, str]:
    """Minimal readiness endpoint; application slices add routes here."""
    return {"status": "ok"}

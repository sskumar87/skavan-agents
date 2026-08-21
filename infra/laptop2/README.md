# Laptop 2 operations

Run `preflight.ps1` from the repository root after copying `.env.example` to
the ignored `.env` and the Compose example to the ignored deployment file:

```powershell
powershell -ExecutionPolicy Bypass -File infra/laptop2/preflight.ps1
```

The check does not print secret values or start/stop services. It verifies that
Docker and Compose are available, required local files exist and are ignored,
deployment placeholders have been replaced, and all optional Compose profiles
render successfully. A nonzero exit blocks deployment.

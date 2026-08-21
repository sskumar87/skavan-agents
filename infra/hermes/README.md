# Hermes Phase 1

From the repository root on Laptop 2:

```powershell
powershell -ExecutionPolicy Bypass -File infra/hermes/configure-phase1.ps1
docker compose --env-file "C:\SKAV_PLATFORM\secrets\skavan-phase1\.env" -f infra/docker/compose.phase1.yml up -d --build
```

The setup prompt masks the required DeepSeek key and optional Anthropic fallback
key. It writes them outside the repository and generates a separate Hermes API
server key. Open `http://127.0.0.1:8080` after all four containers are healthy.

Stop the Phase 1 stack without deleting Hermes state:

```powershell
docker compose --env-file "C:\SKAV_PLATFORM\secrets\skavan-phase1\.env" -f infra/docker/compose.phase1.yml down
```

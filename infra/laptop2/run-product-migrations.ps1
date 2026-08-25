[CmdletBinding()]
param(
    [string]$EnvironmentFile = "C:\SKAV_PLATFORM\secrets\skavan-phase1\.env",
    [string]$RepositoryRoot = "C:\SKAV_PLATFORM\skavan-agents"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $EnvironmentFile)) {
    throw "Protected environment file not found: $EnvironmentFile"
}

$line = Get-Content -LiteralPath $EnvironmentFile |
    Where-Object { $_ -like "SKAVAN_MIGRATION_DATABASE_URL=*" } |
    Select-Object -First 1

if (-not $line) {
    throw @"
SKAVAN_MIGRATION_DATABASE_URL is missing.
Run infra\laptop2\configure-product-database.ps1 and provide the existing
skavan_app and skavan_migrator passwords. Do not use DATABASE_URL for migrations.
"@
}

$migrationUrl = $line.Substring("SKAVAN_MIGRATION_DATABASE_URL=".Length).Trim('"')
$uri = [Uri]$migrationUrl.Replace("postgresql+asyncpg://", "postgresql://")
if ([Uri]::UnescapeDataString($uri.UserInfo.Split(':', 2)[0]) -ne "skavan_migrator") {
    throw "Migration URL must use the skavan_migrator account."
}

$env:SKAVAN_MIGRATION_DATABASE_URL = $migrationUrl
Push-Location -LiteralPath $RepositoryRoot
try {
    uv run --with-requirements database/migrations/requirements.txt `
        alembic -c database/migrations/alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade failed." }

    uv run --with-requirements database/migrations/requirements.txt `
        alembic -c database/migrations/alembic.ini current
    if ($LASTEXITCODE -ne 0) { throw "Alembic revision check failed." }
}
finally {
    Remove-Item Env:\SKAVAN_MIGRATION_DATABASE_URL -ErrorAction SilentlyContinue
    Pop-Location
}

[CmdletBinding()]
param(
    [string]$EnvFile = ".env",
    [string]$ComposeFile = "infra/docker/compose.laptop2.yml"
)

$ErrorActionPreference = "Stop"
$failures = 0

function Pass([string]$Message) { Write-Host "PASS  $Message" -ForegroundColor Green }
function Fail([string]$Message) { Write-Host "FAIL  $Message" -ForegroundColor Red; $script:failures++ }

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Pass "Docker CLI is installed"
} else {
    Fail "Docker CLI is missing"
}

try {
    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -eq 0) { Pass "Docker engine is reachable" } else { Fail "Docker engine is unreachable" }
} catch { Fail "Docker engine is unreachable" }

try {
    docker compose version | Out-Null
    if ($LASTEXITCODE -eq 0) { Pass "Docker Compose is installed" } else { Fail "Docker Compose is unavailable" }
} catch { Fail "Docker Compose is unavailable" }

foreach ($path in @($EnvFile, $ComposeFile)) {
    if (Test-Path -LiteralPath $path -PathType Leaf) { Pass "$path exists" } else { Fail "$path is missing" }
}

if (Test-Path -LiteralPath $EnvFile -PathType Leaf) {
    $configuration = @{}
    $seenNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    foreach ($line in Get-Content -LiteralPath $EnvFile) {
        if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
        $name, $value = $line -split '=', 2
        $name = $name.Trim()
        if (-not $seenNames.Add($name)) { Fail "$name is defined more than once" }
        $configuration[$name] = $value.Trim()
    }

    foreach ($required in @(
        'DATABASE_URL', 'SKAVAN_MIGRATION_DATABASE_URL', 'OIDC_ISSUER_URL',
        'APP_ORIGIN', 'HERMES_API_SERVER_KEY', 'ZITADEL_DOMAIN',
        'ZITADEL_MASTERKEY_FILE', 'ZITADEL_DATABASE_POSTGRES_DSN'
    )) {
        $value = $configuration[$required]
        if ([string]::IsNullOrWhiteSpace($value) -or $value -match 'example\.com|change-me|laptop1\.internal') {
            Fail "$required is missing or still contains a placeholder"
        } else {
            Pass "$required is configured"
        }
    }

    foreach ($urlName in @('OIDC_ISSUER_URL', 'APP_ORIGIN')) {
        $uri = $null
        if (-not [Uri]::TryCreate($configuration[$urlName], [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -ne 'https') {
            Fail "$urlName must be an absolute HTTPS URL"
        }
    }
    $masterKeyFile = $configuration['ZITADEL_MASTERKEY_FILE']
    if (-not [string]::IsNullOrWhiteSpace($masterKeyFile) -and (Test-Path -LiteralPath $masterKeyFile -PathType Leaf)) {
        $masterKey = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $masterKeyFile)).TrimEnd("`r", "`n")
        if ($masterKey.Length -eq 32) { Pass "ZITADEL master-key file contains exactly 32 characters" } else { Fail "ZITADEL master-key file must contain exactly 32 characters" }
        $repositoryRoot = [System.IO.Path]::GetFullPath((Get-Location).Path)
        $resolvedMasterKey = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $masterKeyFile).Path)
        if ($resolvedMasterKey.StartsWith($repositoryRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            Fail "ZITADEL master-key file must be outside the repository"
        } else {
            Pass "ZITADEL master-key file is outside the repository"
        }
        $masterKey = $null
    } else {
        Fail "ZITADEL_MASTERKEY_FILE does not identify a readable file"
    }
    if ($configuration['HERMES_API_SERVER_KEY'].Length -lt 8) { Fail "HERMES_API_SERVER_KEY must contain at least 8 characters" }
    foreach ($dsnName in @('DATABASE_URL', 'SKAVAN_MIGRATION_DATABASE_URL', 'ZITADEL_DATABASE_POSTGRES_DSN')) {
        if ($configuration[$dsnName] -notmatch '(\?|&)sslmode=verify-full(?:&|$)') {
            Fail "$dsnName must require sslmode=verify-full"
        }
    }
    foreach ($imageName in @('CLOUDFLARED_IMAGE', 'NGINX_IMAGE', 'NODE_IMAGE', 'PYTHON_IMAGE', 'ZITADEL_IMAGE', 'ZITADEL_LOGIN_IMAGE', 'TRAEFIK_IMAGE', 'HERMES_IMAGE')) {
        if ($configuration[$imageName] -notmatch '@sha256:[0-9a-f]{64}$') { Fail "$imageName must use an immutable sha256 digest" }
    }
}

foreach ($path in @($EnvFile, $ComposeFile)) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        git check-ignore --quiet -- $path
        if ($LASTEXITCODE -eq 0) { Pass "$path is ignored by Git" } else { Fail "$path is not ignored by Git" }
    }
}

if ((Get-Command docker -ErrorAction SilentlyContinue) -and
    (Test-Path -LiteralPath $EnvFile -PathType Leaf) -and
    (Test-Path -LiteralPath $ComposeFile -PathType Leaf)) {
    $composeJson = docker compose --env-file $EnvFile -f $ComposeFile --profile identity --profile hermes config --format json 2>$null | Out-String
    if ($LASTEXITCODE -eq 0) {
        Pass "all Compose profiles are valid"
        $model = $composeJson | ConvertFrom-Json
        $serviceNames = @($model.services.PSObject.Properties.Name)
        foreach ($forbidden in @('postgres', 'postgresql', 'redis', 'redisinsight')) {
            if ($serviceNames -contains $forbidden) { Fail "forbidden Laptop 2 service is present: $forbidden" }
        }
        foreach ($serviceProperty in $model.services.PSObject.Properties) {
            if (@($serviceProperty.Value.ports).Count -gt 0) { Fail "$($serviceProperty.Name) publishes a host port" }
            if ($serviceProperty.Value.image -and $serviceProperty.Value.image -notmatch '@sha256:[0-9a-f]{64}$') {
                Fail "$($serviceProperty.Name) image is not digest-pinned"
            }
        }

        $allowedEnvironment = @{
            web = @('NODE_ENV', 'NEXT_PUBLIC_APP_ORIGIN')
            api = @('DATABASE_URL', 'OIDC_ISSUER_URL', 'OIDC_CLIENT_ID', 'HERMES_API_BASE_URL', 'HERMES_API_SERVER_KEY')
            hermes = @('API_SERVER_ENABLED', 'API_SERVER_HOST', 'API_SERVER_KEY', 'HERMES_DASHBOARD')
        }
        foreach ($serviceName in $allowedEnvironment.Keys) {
            $environmentNames = @($model.services.$serviceName.environment.PSObject.Properties.Name)
            $unexpected = @($environmentNames | Where-Object { $_ -notin $allowedEnvironment[$serviceName] })
            if ($unexpected.Count -eq 0) {
                Pass "$serviceName receives only its approved environment variables"
            } else {
                Fail "$serviceName receives unapproved environment variable names: $($unexpected -join ', ')"
            }
        }
    } else {
        Fail "Compose validation failed"
    }
}

Write-Host "`nPreflight result: $failures failure(s)."
if ($failures -gt 0) { exit 1 }

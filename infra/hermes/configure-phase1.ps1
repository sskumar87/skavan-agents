[CmdletBinding()]
param(
    [string]$DataDirectory = "C:\SKAV_PLATFORM\secrets\skavan-phase1"
)

$ErrorActionPreference = "Stop"
$deepSeekKey = Read-Host "DeepSeek API key" -MaskInput
if ([string]::IsNullOrWhiteSpace($deepSeekKey)) {
    throw "A DeepSeek API key is required."
}
$anthropicKey = Read-Host "Anthropic API key (optional fallback; press Enter to skip)" -MaskInput
$dashboardUsername = Read-Host "Hermes dashboard username (press Enter for admin)"
if ([string]::IsNullOrWhiteSpace($dashboardUsername)) {
    $dashboardUsername = "admin"
}
$dashboardPassword = Read-Host "Hermes dashboard password" -MaskInput
if ([string]::IsNullOrWhiteSpace($dashboardPassword)) {
    throw "A Hermes dashboard password is required."
}
$hermesServerKey = [Convert]::ToHexString(
    [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
).ToLowerInvariant()
$dashboardSecret = [Convert]::ToHexString(
    [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
).ToLowerInvariant()

New-Item -ItemType Directory -Path $DataDirectory -Force | Out-Null
$dockerDataDirectory = $DataDirectory.Replace('\', '/')

$environmentLines = @(
    "HERMES_API_SERVER_KEY=$hermesServerKey"
    "API_SERVER_KEY=$hermesServerKey"
    "DEEPSEEK_API_KEY=$deepSeekKey"
    "ANTHROPIC_API_KEY=$anthropicKey"
    "HERMES_DASHBOARD_BASIC_AUTH_USERNAME=$dashboardUsername"
    "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=$dashboardPassword"
    "HERMES_DASHBOARD_BASIC_AUTH_SECRET=$dashboardSecret"
    "HERMES_DATA_DIR=$dockerDataDirectory"
)
[System.IO.File]::WriteAllLines((Join-Path $DataDirectory ".env"), $environmentLines)

$configurationLines = @(
    "_config_version: 12"
    "model:"
    "  provider: deepseek"
    "  default: deepseek-chat"
)
if (-not [string]::IsNullOrWhiteSpace($anthropicKey)) {
    $configurationLines += @(
        "fallback_providers:"
        "  - provider: anthropic"
        "    model: claude-sonnet-4-6"
    )
}
[System.IO.File]::WriteAllLines((Join-Path $DataDirectory "config.yaml"), $configurationLines)

$deepSeekKey = $null
$anthropicKey = $null
$dashboardUsername = $null
$dashboardPassword = $null
$hermesServerKey = $null
$dashboardSecret = $null

Write-Host "Phase 1 Hermes configuration created outside the repository: $DataDirectory"
Write-Host "Start with: docker compose --env-file `"$DataDirectory\.env`" -f infra/docker/compose.phase1.yml up -d --build"

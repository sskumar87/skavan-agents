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
function New-RandomHexKey {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ([BitConverter]::ToString($bytes) -replace "-", "").ToLowerInvariant()
}
$hermesServerKey = New-RandomHexKey
$personalServerKey = New-RandomHexKey
$workServerKey = New-RandomHexKey
$dashboardSecret = New-RandomHexKey

New-Item -ItemType Directory -Path $DataDirectory -Force | Out-Null
$hermesDataDirectory = Join-Path $DataDirectory "hermes"
New-Item -ItemType Directory -Path $hermesDataDirectory -Force | Out-Null
$dockerDataDirectory = $hermesDataDirectory.Replace('\', '/')

$environmentLines = @(
    "HERMES_API_SERVER_KEY=$hermesServerKey"
    "HERMES_PERSONAL_API_SERVER_KEY=$personalServerKey"
    "HERMES_WORK_API_SERVER_KEY=$workServerKey"
    "DEEPSEEK_API_KEY=$deepSeekKey"
    "ANTHROPIC_API_KEY=$anthropicKey"
    "HERMES_DASHBOARD_BASIC_AUTH_USERNAME=$dashboardUsername"
    "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=$dashboardPassword"
    "HERMES_DASHBOARD_BASIC_AUTH_SECRET=$dashboardSecret"
    "HERMES_DATA_DIR=$dockerDataDirectory"
    "SKAV_PLATFORM_DIR=C:/SKAV_PLATFORM"
)
[System.IO.File]::WriteAllLines((Join-Path $DataDirectory ".env"), $environmentLines)

$providerLines = @("DEEPSEEK_API_KEY=$deepSeekKey")
if (-not [string]::IsNullOrWhiteSpace($anthropicKey)) {
    $providerLines += "ANTHROPIC_API_KEY=$anthropicKey"
}
[System.IO.File]::WriteAllLines((Join-Path $hermesDataDirectory ".env"), @(
    "API_SERVER_KEY=$hermesServerKey"
) + $providerLines)

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
$profileConfigurationLines = [string[]]$configurationLines
$configurationLines += @(
    "gateway:"
    "  multiplex_profiles: true"
    "  multiplex_profile_allowlist:"
    "    - personal"
    "    - work"
)
[System.IO.File]::WriteAllLines((Join-Path $hermesDataDirectory "config.yaml"), $configurationLines)
foreach ($profile in @("personal", "work")) {
    $profileDirectory = Join-Path $hermesDataDirectory "profiles\$profile"
    New-Item -ItemType Directory -Path $profileDirectory -Force | Out-Null
    [System.IO.File]::WriteAllLines(
        (Join-Path $profileDirectory "config.yaml"),
        $profileConfigurationLines
    )
    $profileKey = if ($profile -eq "personal") { $personalServerKey } else { $workServerKey }
    [System.IO.File]::WriteAllLines((Join-Path $profileDirectory ".env"), @(
        "API_SERVER_KEY=$profileKey"
    ) + $providerLines)
}

$deepSeekKey = $null
$anthropicKey = $null
$dashboardUsername = $null
$dashboardPassword = $null
$hermesServerKey = $null
$personalServerKey = $null
$workServerKey = $null
$dashboardSecret = $null

Write-Host "Phase 1 Hermes configuration created outside the repository: $DataDirectory"
Write-Host "Start with: docker compose --env-file `"$DataDirectory\.env`" -f infra/docker/compose.phase1.yml up -d --build"

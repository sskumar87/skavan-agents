[CmdletBinding()]
param(
    [string]$SecretsDirectory = "C:\SKAV_PLATFORM\secrets\skavan-phase1"
)

$ErrorActionPreference = "Stop"
$sourceEnv = Join-Path $SecretsDirectory ".env"
$hermesDirectory = Join-Path $SecretsDirectory "hermes"
if (-not (Test-Path -LiteralPath $sourceEnv -PathType Leaf)) {
    throw "Phase 1 environment file not found: $sourceEnv"
}
if (Test-Path -LiteralPath $hermesDirectory) {
    throw "Hermes directory already exists. Review it instead of overwriting it: $hermesDirectory"
}

function Read-EnvironmentFile([string]$Path) {
    $values = [ordered]@{}
    foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith("#")) { continue }
        $separator = $line.IndexOf("=")
        if ($separator -lt 1) { continue }
        $values[$line.Substring(0, $separator)] = $line.Substring($separator + 1)
    }
    return $values
}

function New-RandomHexKey {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ([BitConverter]::ToString($bytes) -replace "-", "").ToLowerInvariant()
}

function Set-EnvironmentValue([string]$Path, [string]$Name, [string]$Value) {
    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.AddRange([string[]][System.IO.File]::ReadAllLines($Path))
    $prefix = "$Name="
    $index = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].StartsWith($prefix, [StringComparison]::Ordinal)) { $index = $i; break }
    }
    if ($index -ge 0) { $lines[$index] = "$prefix$Value" } else { $lines.Add("$prefix$Value") }
    [System.IO.File]::WriteAllLines($Path, $lines)
}

$environment = Read-EnvironmentFile $sourceEnv
foreach ($required in @("HERMES_API_SERVER_KEY", "DEEPSEEK_API_KEY")) {
    if (-not $environment.Contains($required) -or [string]::IsNullOrWhiteSpace($environment[$required])) {
        throw "$required is missing from $sourceEnv"
    }
}

$personalKey = if ($environment.Contains("HERMES_PERSONAL_API_SERVER_KEY") -and $environment["HERMES_PERSONAL_API_SERVER_KEY"]) {
    $environment["HERMES_PERSONAL_API_SERVER_KEY"]
} else { New-RandomHexKey }
$workKey = if ($environment.Contains("HERMES_WORK_API_SERVER_KEY") -and $environment["HERMES_WORK_API_SERVER_KEY"]) {
    $environment["HERMES_WORK_API_SERVER_KEY"]
} else { New-RandomHexKey }

New-Item -ItemType Directory -Path $hermesDirectory | Out-Null
$excludedNames = @(".env", "zitadel-create.sql", "zitadel-masterkey")
Get-ChildItem -LiteralPath $SecretsDirectory -Force | Where-Object {
    $_.Name -ne "hermes" -and
    $_.Name -notlike ".env.bak-*" -and
    $_.Name -notin $excludedNames
} | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $hermesDirectory -Recurse
}

$baseConfiguration = Join-Path $hermesDirectory "config.yaml"
$baseSoul = Join-Path $hermesDirectory "SOUL.md"
foreach ($profile in @("personal", "work")) {
    $profileDirectory = Join-Path $hermesDirectory "profiles\$profile"
    New-Item -ItemType Directory -Path $profileDirectory -Force | Out-Null
    Copy-Item -LiteralPath $baseConfiguration -Destination (Join-Path $profileDirectory "config.yaml")
    if (Test-Path -LiteralPath $baseSoul) {
        Copy-Item -LiteralPath $baseSoul -Destination (Join-Path $profileDirectory "SOUL.md")
    }
    $sourceSkills = Join-Path $hermesDirectory "skills"
    if (Test-Path -LiteralPath $sourceSkills) {
        Copy-Item -LiteralPath $sourceSkills -Destination (Join-Path $profileDirectory "skills") -Recurse
    }
}

$providerLines = @("DEEPSEEK_API_KEY=$($environment['DEEPSEEK_API_KEY'])")
if ($environment.Contains("ANTHROPIC_API_KEY") -and $environment["ANTHROPIC_API_KEY"]) {
    $providerLines += "ANTHROPIC_API_KEY=$($environment['ANTHROPIC_API_KEY'])"
}
[System.IO.File]::WriteAllLines((Join-Path $hermesDirectory ".env"), @(
    "API_SERVER_KEY=$($environment['HERMES_API_SERVER_KEY'])"
) + $providerLines)
[System.IO.File]::WriteAllLines((Join-Path $hermesDirectory "profiles\personal\.env"), @(
    "API_SERVER_KEY=$personalKey"
) + $providerLines)
[System.IO.File]::WriteAllLines((Join-Path $hermesDirectory "profiles\work\.env"), @(
    "API_SERVER_KEY=$workKey"
) + $providerLines)

[System.IO.File]::AppendAllLines($baseConfiguration, @(
    ""
    "gateway:"
    "  multiplex_profiles: true"
    "  multiplex_profile_allowlist:"
    "    - personal"
    "    - work"
))

Set-EnvironmentValue $sourceEnv "HERMES_PERSONAL_API_SERVER_KEY" $personalKey
Set-EnvironmentValue $sourceEnv "HERMES_WORK_API_SERVER_KEY" $workKey
Set-EnvironmentValue $sourceEnv "HERMES_DATA_DIR" ($hermesDirectory.Replace("\", "/"))

$personalKey = $null
$workKey = $null
$environment = $null
Write-Host "Hermes data copied to the dedicated directory: $hermesDirectory"
Write-Host "Created Personal and Work profile configuration without copying the platform environment file."
Write-Host "No containers were restarted. Review the files, then rebuild the API and restart Hermes."

[CmdletBinding()]
param(
    [string]$SecretsDirectory = "C:\SKAV_PLATFORM\secrets\skavan-phase1"
)

$ErrorActionPreference = "Stop"

function Read-EnvironmentValue([string]$Path, [string]$Name) {
    foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
        if ($line.StartsWith("$Name=", [StringComparison]::Ordinal)) {
            return $line.Substring($Name.Length + 1)
        }
    }
    return ""
}

function Set-EnvironmentValue([string]$Path, [string]$Name, [string]$Value) {
    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.AddRange([string[]][System.IO.File]::ReadAllLines($Path))
    $prefix = "$Name="
    $index = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].StartsWith($prefix, [StringComparison]::Ordinal)) {
            $index = $i
            break
        }
    }
    if ($index -ge 0) {
        $lines[$index] = "$prefix$Value"
    } else {
        $lines.Add("$prefix$Value")
    }
    [System.IO.File]::WriteAllLines($Path, $lines)
}

$platformEnvironment = Join-Path $SecretsDirectory ".env"
$workEnvironment = Join-Path $SecretsDirectory "hermes\profiles\work\.env"

if (-not (Test-Path -LiteralPath $platformEnvironment -PathType Leaf)) {
    throw "Platform environment file not found: $platformEnvironment"
}
if (-not (Test-Path -LiteralPath $workEnvironment -PathType Leaf)) {
    throw "Work profile environment file not found: $workEnvironment"
}

$workKey = Read-EnvironmentValue $platformEnvironment "HERMES_WORK_API_SERVER_KEY"
if ([string]::IsNullOrWhiteSpace($workKey) -or $workKey.Length -lt 16) {
    throw "HERMES_WORK_API_SERVER_KEY is missing or invalid in $platformEnvironment"
}

Set-EnvironmentValue $workEnvironment "API_SERVER_KEY" $workKey
$workKey = $null

Write-Host "Work profile API key synchronized. No secret value was printed."

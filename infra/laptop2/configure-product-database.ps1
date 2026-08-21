[CmdletBinding()]
param(
    [string]$SecretDirectory = "C:\SKAV_PLATFORM\secrets\skavan-phase1",
    [string]$DatabaseHost = "192.168.1.49",
    [int]$DatabasePort = 5432,
    [string]$DatabaseName = "skavan",
    [string]$DatabaseUser = "skavan_app"
)

$ErrorActionPreference = "Stop"

function ConvertTo-PlainText([Security.SecureString]$Value) {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Set-EnvironmentValue([string]$Path, [string]$Name, [string]$Value) {
    $lines = @(
        if (Test-Path -LiteralPath $Path) {
            Get-Content -LiteralPath $Path
        }
    )
    $replacement = "$Name=$Value"
    $found = $false

    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match "^$([regex]::Escape($Name))=") {
            $lines[$index] = $replacement
            $found = $true
        }
    }

    if (-not $found) { $lines += $replacement }
    Set-Content -LiteralPath $Path -Value $lines -Encoding utf8
}

New-Item -ItemType Directory -Path $SecretDirectory -Force | Out-Null
$environmentFile = Join-Path $SecretDirectory ".env"
$databasePassword = ConvertTo-PlainText (
    Read-Host "Existing PostgreSQL password for '$DatabaseUser'" -AsSecureString
)

if ([string]::IsNullOrWhiteSpace($databasePassword)) {
    throw "The database password cannot be empty."
}

$encodedUser = [Uri]::EscapeDataString($DatabaseUser)
$encodedPassword = [Uri]::EscapeDataString($databasePassword)
$encodedDatabase = [Uri]::EscapeDataString($DatabaseName)
$databaseUrl = "postgresql+asyncpg://$encodedUser`:$encodedPassword@$DatabaseHost`:$DatabasePort/$encodedDatabase"

Set-EnvironmentValue $environmentFile "DATABASE_URL" $databaseUrl

Write-Host "Product database configuration saved without displaying the password."
Write-Host "Environment: $environmentFile"

[CmdletBinding()]
param(
    [string]$SecretDirectory = "C:\SKAV_PLATFORM\secrets\skavan-phase1",
    [string]$DatabaseHost = "192.168.1.49",
    [int]$DatabasePort = 5432,
    [string]$AppOrigin = "https://skavan.skavapp.com",
    [string]$ZitadelIssuerUrl = "https://auth.skavapp.com"
)

$ErrorActionPreference = "Stop"

function New-HexSecret([int]$ByteCount) {
    $bytes = New-Object byte[] $ByteCount
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
}

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
$masterKeyFile = Join-Path $SecretDirectory "zitadel-masterkey"
$databaseSqlFile = Join-Path $SecretDirectory "zitadel-create.sql"

$databasePassword = ConvertTo-PlainText (Read-Host "New password for the dedicated PostgreSQL role 'zitadel'" -AsSecureString)
$adminPassword = ConvertTo-PlainText (Read-Host "Initial ZITADEL administrator password" -AsSecureString)

if ($databasePassword.Length -lt 16) { throw "The database password must contain at least 16 characters." }
if ($adminPassword.Length -lt 12 -or $adminPassword -notmatch '[A-Z]' -or $adminPassword -notmatch '[a-z]' -or $adminPassword -notmatch '\d' -or $adminPassword -notmatch '[^A-Za-z0-9]') {
    throw "The administrator password must be at least 12 characters and include upper, lower, number, and symbol characters."
}

$masterKey = New-HexSecret 16
$authSecret = New-HexSecret 32
$issuerUri = [Uri]$ZitadelIssuerUrl
$issuerUrl = $issuerUri.AbsoluteUri.TrimEnd('/')
$externalSecure = if ($issuerUri.Scheme -eq 'https') { 'true' } else { 'false' }
$externalPort = if ($issuerUri.IsDefaultPort) {
    if ($issuerUri.Scheme -eq 'https') { 443 } else { 80 }
} else {
    $issuerUri.Port
}
$encodedDatabasePassword = [Uri]::EscapeDataString($databasePassword)
$databaseDsn = "postgresql://zitadel:$encodedDatabasePassword@$DatabaseHost`:$DatabasePort/zitadel?sslmode=disable"

Set-Content -LiteralPath $masterKeyFile -Value $masterKey -NoNewline -Encoding ascii
Set-EnvironmentValue $environmentFile "AUTH_SECRET" $authSecret
Set-EnvironmentValue $environmentFile "AUTH_TRUST_HOST" "true"
Set-EnvironmentValue $environmentFile "AUTH_SESSION_MAX_AGE" "3600"
Set-EnvironmentValue $environmentFile "APP_ORIGIN" $AppOrigin.TrimEnd('/')
Set-EnvironmentValue $environmentFile "ZITADEL_DOMAIN" $issuerUri.Host
Set-EnvironmentValue $environmentFile "ZITADEL_EXTERNAL_PORT" "$externalPort"
Set-EnvironmentValue $environmentFile "ZITADEL_EXTERNAL_SECURE" $externalSecure
Set-EnvironmentValue $environmentFile "ZITADEL_EXTERNAL_SCHEME" $issuerUri.Scheme
Set-EnvironmentValue $environmentFile "ZITADEL_ISSUER_URL" $issuerUrl
Set-EnvironmentValue $environmentFile "ZITADEL_CLIENT_ID" "bootstrap-pending"
Set-EnvironmentValue $environmentFile "ZITADEL_DATABASE_POSTGRES_DSN" $databaseDsn
Set-EnvironmentValue $environmentFile "ZITADEL_MASTERKEY_FILE" ($masterKeyFile -replace '\\', '/')
Set-EnvironmentValue $environmentFile "ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORD" $adminPassword
Set-EnvironmentValue $environmentFile "LOGIN_CLIENT_PAT_EXPIRATION" "2027-08-21T00:00:00Z"

$escapedSqlPassword = $databasePassword.Replace("'", "''")
$databaseSql = @"
-- Run once from an administrative connection to the existing Laptop 1 server.
-- This safely creates the role or rotates its password when it already exists.
DO `$zitadel_role`$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zitadel') THEN
        ALTER ROLE zitadel WITH LOGIN PASSWORD '$escapedSqlPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    ELSE
        CREATE ROLE zitadel LOGIN PASSWORD '$escapedSqlPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    END IF;
END
`$zitadel_role`$;

-- The phase-one database already exists; this keeps its ownership explicit.
ALTER DATABASE zitadel OWNER TO zitadel;
"@
Set-Content -LiteralPath $databaseSqlFile -Value $databaseSql -Encoding utf8

Write-Host "Prepared login configuration without displaying any secret values."
Write-Host "Environment: $environmentFile"
Write-Host "Database SQL: $databaseSqlFile"
Write-Host "Next: run the SQL once in IntelliJ against Laptop 1, then start the identity profile."

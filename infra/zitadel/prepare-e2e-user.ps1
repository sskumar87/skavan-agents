[CmdletBinding()]
param(
    [string]$SecretDirectory = "C:\SKAV_PLATFORM\secrets\skavan-phase1\test-users",
    [string]$FileName = "codex-e2e.json"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Path $SecretDirectory -Force | Out-Null
$credentialFile = Join-Path $SecretDirectory $FileName

if (Test-Path -LiteralPath $credentialFile) {
    Write-Host "Reusing existing test credential file: $credentialFile"
    exit 0
}

$bytes = New-Object byte[] 24
$generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $generator.GetBytes($bytes)
}
finally {
    $generator.Dispose()
}

$random = ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
$credential = [ordered]@{
    login_name = "codex-e2e"
    email = "codex-e2e@skavapp.test"
    first_name = "Codex"
    last_name = "E2E"
    password = "Aa1!$random"
    purpose = "Non-admin Skavan end-to-end development testing"
}

$credential | ConvertTo-Json | Set-Content -LiteralPath $credentialFile -Encoding utf8
Write-Host "Prepared test credentials without displaying the password: $credentialFile"

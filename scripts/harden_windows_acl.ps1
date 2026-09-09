param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
)

$ErrorActionPreference = "Stop"
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$directories = @(
    (Join-Path $ProjectRoot "private"),
    (Join-Path $ProjectRoot "workspace")
)

foreach ($target in $directories) {
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    & icacls.exe $target /inheritance:r | Out-Null
    & icacls.exe $target /grant:r "${identity}:(OI)(CI)F" "SYSTEM:(OI)(CI)F" | Out-Null
    & icacls.exe $target /remove:g "Users" "Authenticated Users" "Everyone" 2>$null | Out-Null
    Write-Host "Hardened directory ACL: $target"
}

$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path -LiteralPath $envFile) {
    & icacls.exe $envFile /inheritance:r | Out-Null
    & icacls.exe $envFile /grant:r "${identity}:F" "SYSTEM:F" | Out-Null
    & icacls.exe $envFile /remove:g "Users" "Authenticated Users" "Everyone" 2>$null | Out-Null
    Write-Host "Hardened secret file ACL: $envFile"
} else {
    Write-Host "Skipped .env ACL because the file does not exist yet. Run this script again after saving DeepSeek settings."
}

Write-Host "Only $identity and SYSTEM have explicit access."
Write-Host "Bedrock runs as $identity, so it shares this user's OS identity."

# Run on a disposable Windows CI runner; never start Docker or open a browser.
$ErrorActionPreference = 'Stop'
$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path (Join-Path $temporaryRoot 'deploy') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $temporaryRoot 'fablab-face-attendance') | Out-Null
$scriptPath = Join-Path $temporaryRoot 'deploy\showcase-windows.ps1'
Copy-Item (Join-Path $PSScriptRoot 'showcase-windows.ps1') $scriptPath
$envPath = Join-Path $temporaryRoot 'fablab-face-attendance\.env'
$original = "# Existing private configuration`nSESSION_SECRET_KEY=keep-this-signing-key`n"
[IO.File]::WriteAllText($envPath, $original)
$script:opened = @()
$script:dockerCalls = @()

function docker {
    $script:dockerCalls += ($args -join ' ')
    $global:LASTEXITCODE = 0
}
function Read-Host { throw 'Repeat startup must never prompt for credentials.' }
function Start-Sleep { }
function Start-Process { param($FilePath) $script:opened += $FilePath }
function Invoke-RestMethod {
    return @{ database='ready'; cv_engine='not_loaded'; telegram=@{configured=$false};
        security=@{admin_password_configured=$true; session_secret_configured=$true} }
}

try {
    $parseErrors = $null
    [Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$null, [ref]$parseErrors) | Out-Null
    if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
    & $scriptPath -SkipTelegram
    & $scriptPath -SkipTelegram
    if ([IO.File]::ReadAllText($envPath) -cne $original) { throw 'Repeat startup changed saved credentials.' }
    if ($script:opened.Count -ne 2 -or $script:opened[0] -ne 'http://localhost:8090') { throw 'Launcher did not open the local website.' }
    if (($script:dockerCalls | Where-Object { $_ -eq 'compose up --build -d' }).Count -ne 2) { throw 'Launcher did not start Compose.' }
    Write-Host 'Windows repeat startup preserves saved configuration and opens the local website: PASS'
} finally {
    Remove-Item -Recurse -Force $temporaryRoot
}

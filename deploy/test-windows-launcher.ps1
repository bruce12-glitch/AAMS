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
$global:AamsLauncherTestState = @{
    Opened = New-Object 'Collections.Generic.List[string]'
    DockerCalls = New-Object 'Collections.Generic.List[string]'
}

function docker {
    $global:AamsLauncherTestState.DockerCalls.Add(($args -join ' '))
    $global:LASTEXITCODE = 0
}
function Read-Host { throw 'Repeat startup must never prompt for credentials.' }
function Start-Sleep { }
function Start-Process { param($FilePath) $global:AamsLauncherTestState.Opened.Add($FilePath) }
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
    if ($global:AamsLauncherTestState.Opened.Count -ne 2 -or $global:AamsLauncherTestState.Opened[0] -ne 'http://localhost:8090') { throw 'Launcher did not open the local website.' }
    if (($global:AamsLauncherTestState.DockerCalls | Where-Object { $_ -eq 'compose up --build -d' }).Count -ne 2) { throw 'Launcher did not start Compose.' }
    Write-Host 'Windows repeat startup preserves saved configuration and opens the local website: PASS'

    # First-run setup must serialize KEY=value as ONE line, including empty
    # Telegram fields. The old test only covered an already-existing .env.
    Remove-Item -LiteralPath $envPath
    function Read-Host {
        param([string]$Prompt, [switch]$AsSecureString)
        if ($Prompt -eq 'Administrator SRMIST email') { return 'launcher-test@srmist.edu.in' }
        $value = if ($Prompt -like 'Choose administrator*') { 'launcher-test-admin-credential' } else { 'launcher-test-member-credential' }
        return ConvertTo-SecureString $value -AsPlainText -Force
    }
    & $scriptPath -SkipTelegram
    $lines = [IO.File]::ReadAllLines($envPath)
    if ($lines.Length -ne 11) { throw 'First-run environment values were split over multiple lines.' }
    foreach ($line in $lines | Select-Object -Skip 1) {
        if ($line -notmatch '^[A-Z_]+=.*$') { throw 'First-run environment contains an invalid assignment.' }
    }
    $generated = [IO.File]::ReadAllText($envPath)
    & $scriptPath -SkipTelegram
    if ([IO.File]::ReadAllText($envPath) -cne $generated) { throw 'Restart changed first-run credentials.' }
    Write-Host 'Windows first-run configuration produces complete dotenv assignments: PASS'
} finally {
    Remove-Item -Recurse -Force $temporaryRoot
    Remove-Variable -Name AamsLauncherTestState -Scope Global
}

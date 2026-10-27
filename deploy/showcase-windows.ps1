[CmdletBinding()]
param(
    [string]$AdminEmail,
    [switch]$PublicUrl,
    [switch]$SkipTelegram
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendEnv = Join-Path $RepoRoot 'fablab-face-attendance\.env'

function ConvertFrom-SecureValue([Security.SecureString]$Value) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function New-RandomSecret {
    $bytes = New-Object byte[] 48
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Format-EnvValue([string]$Value) {
    if ($Value -match "[\r\n]") { throw 'Environment values cannot contain newlines.' }
    return "'" + $Value.Replace("'", "\'") + "'"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker Desktop was not found. Install/start Docker Desktop, then run this script again.'
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop is installed but not running.' }

function Initialize-LocalConfiguration {
if (-not $AdminEmail) { $AdminEmail = Read-Host 'Administrator SRMIST email' }
$AdminEmail = $AdminEmail.Trim().ToLowerInvariant()
if ($AdminEmail -notmatch '^[a-z0-9._%+-]+@srmist\.edu\.in$') {
    throw 'Administrator email must end in @srmist.edu.in.'
}

$AdminPassword = ConvertFrom-SecureValue (Read-Host 'Choose administrator password (12+ characters)' -AsSecureString)
if ($AdminPassword.Length -lt 12) { throw 'Administrator password must contain at least 12 characters.' }
$AccessPassword = ConvertFrom-SecureValue (Read-Host 'Enter shared AAMS login password (12+ characters)' -AsSecureString)
if ($AccessPassword.Length -lt 12) { throw 'Shared AAMS login password must contain at least 12 characters.' }

if ($AdminPassword -ceq $AccessPassword) { throw 'Administrator and shared credentials must be different.' }

$TelegramToken = ''
$TelegramChat = ''
if (-not $SkipTelegram) {
    $configureTelegram = Read-Host 'Configure Telegram now? (y/N)'
    if ($configureTelegram -match '^[Yy]') {
        $TelegramToken = ConvertFrom-SecureValue (Read-Host 'Telegram bot token' -AsSecureString)
        $TelegramChat = (Read-Host 'Telegram chat ID').Trim()
    }
}

$values = @(
    '# Generated locally by deploy/showcase-windows.ps1; never commit this file.',
    ('ADMIN_EMAIL=' + (Format-EnvValue $AdminEmail)),
    ('API_ADMIN_PASSWORD=' + (Format-EnvValue $AdminPassword)),
    ('AAMS_ACCESS_PASSWORD=' + (Format-EnvValue $AccessPassword)),
    ('QR_SECRET_KEY=' + (Format-EnvValue (New-RandomSecret))),
    ('SESSION_SECRET_KEY=' + (Format-EnvValue (New-RandomSecret))),
    'SESSION_TTL_SECONDS=28800',
    'AAMS_ENV=production',
    'DATABASE_PATH=database/fablab.db',
    ('TELEGRAM_BOT_TOKEN=' + (Format-EnvValue $TelegramToken)),
    ('TELEGRAM_CHAT_ID=' + (Format-EnvValue $TelegramChat))
)
[IO.File]::WriteAllLines($BackendEnv, $values, (New-Object Text.UTF8Encoding($false)))
$AdminPassword = $null
$AccessPassword = $null
$TelegramToken = $null
}

if (Test-Path $BackendEnv) {
    Write-Host 'Using saved AAMS configuration. Passwords and QR/session signing keys are preserved.'
} else {
    Initialize-LocalConfiguration
}

Push-Location $RepoRoot
try {
    $profileArgs = @()
    if ($PublicUrl) { $profileArgs = @('--profile', 'showcase') }
    & docker compose @profileArgs up --build -d
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose failed to start AAMS.' }

    $ready = $false
    foreach ($attempt in 1..30) {
        Start-Sleep -Seconds 2
        try {
            $status = Invoke-RestMethod -Uri 'http://localhost:8000/ready' -TimeoutSec 5
            if ($status.database -eq 'ready') { $ready = $true; break }
        } catch { }
    }
    if (-not $ready) {
        docker compose logs --tail 80 api
        throw 'AAMS did not become ready. The API logs are shown above.'
    }

    Write-Host ''
    Write-Host 'AAMS website is running: http://localhost:8090' -ForegroundColor Green
    Write-Host ('Security: admin={0}, sessions={1}' -f `
        $status.security.admin_password_configured, $status.security.session_secret_configured)
    Write-Host ('Telegram configured: {0}' -f $status.telegram.configured)
    Write-Host ('Face model: {0}' -f $status.cv_engine)
    Write-Host 'Sign in -> Dashboard -> Initialize face model. Complete the Prototype setup checks before your demo.'
    Write-Host 'Members -> Enroll face -> Use webcam. Then Live Monitor -> Start webcam attendance.'
    Start-Process 'http://localhost:8090'

    if ($PublicUrl) {
        foreach ($attempt in 1..20) {
            Start-Sleep -Seconds 2
            $logs = docker compose --profile showcase logs --no-color tunnel-quick 2>$null
            $match = [regex]::Match(($logs -join "`n"), 'https://[a-z0-9-]+\.trycloudflare\.com')
            if ($match.Success) {
                Write-Host ('Public showcase: ' + $match.Value) -ForegroundColor Cyan
                break
            }
        }
        if (-not $match.Success) {
            Write-Host 'Tunnel is starting. Run: docker compose --profile showcase logs -f tunnel-quick'
        }
    }
} finally {
    Pop-Location
}

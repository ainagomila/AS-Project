$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

function Test-NssCertutil {
    $commands = @(Get-Command certutil -All -ErrorAction SilentlyContinue)
    return $commands | Where-Object {
        $_.Source -and
        $_.Source -notlike "$env:SystemRoot\System32\*" -and
        $_.Source -notlike "$env:SystemRoot\SysWOW64\*"
    } | Select-Object -First 1
}

function Test-FirefoxInstalled {
    return (
        (Get-Command firefox -ErrorAction SilentlyContinue) -or
        (Test-Path "${env:ProgramFiles}\Mozilla Firefox\firefox.exe") -or
        (Test-Path "${env:ProgramFiles(x86)}\Mozilla Firefox\firefox.exe")
    )
}

if (-not (Get-Command mkcert -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "mkcert is missing and winget is unavailable. Install mkcert from https://github.com/FiloSottile/mkcert"
    }
    Write-Host "mkcert not found. Installing it with winget..."
    winget install --id FiloSottile.mkcert --exact --source winget `
        --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
        [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not (Get-Command mkcert -ErrorAction SilentlyContinue)) {
        throw "mkcert was installed, but is not available in this PowerShell session. Open a new PowerShell window and run this script again."
    }
}

if ((Test-FirefoxInstalled) -and -not (Test-NssCertutil)) {
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Host "NSS certutil not found. Installing it for Firefox support..."
        choco install nss -y
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "User")
    }

    if (-not (Test-NssCertutil)) {
        Write-Warning "Firefox is installed but NSS certutil is unavailable. Chrome and Edge use the Windows trust store; Firefox may still show the certificate as untrusted. Install NSS with 'choco install nss -y', or import the root certificate from 'mkcert -CAROOT' into Firefox."
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required. Start Docker Desktop and try again."
}

Write-Host "Creating and trusting the local HTTPS certificate..."
Set-Location (Join-Path $projectRoot "backend")
New-Item -ItemType Directory -Force .certs | Out-Null
mkcert -install
mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1 backend

Set-Location $projectRoot
Write-Host "Starting Docker Compose..."
docker compose up --build

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

if (Get-Command openssl -ErrorAction SilentlyContinue) {
    $csrPath = ".certs\kofre-bank.csr"
    $keyPath = ".certs\kofre-bank.key"
    openssl req -new -newkey rsa:2048 -nodes `
        -keyout $keyPath -out $csrPath `
        -subj "/C=ES/O=Kofre Bank/OU=Local Development/CN=Kofre Bank Development" `
        -addext "subjectAltName=DNS:kofre-bank.test,DNS:localhost,DNS:backend,IP:127.0.0.1,IP:::1"
    if ($LASTEXITCODE -ne 0) {
        throw "OpenSSL could not create the Kofre Bank certificate request."
    }
    mkcert -csr $csrPath -cert-file .certs/localhost.pem
    if ($LASTEXITCODE -ne 0) {
        throw "mkcert could not sign the Kofre Bank certificate."
    }
    Move-Item -Force $keyPath .certs\localhost-key.pem
    Remove-Item -Force $csrPath
} else {
    Write-Warning "OpenSSL is not installed. Generating a standard mkcert certificate without the formal Kofre Bank subject."
    mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem kofre-bank.test localhost 127.0.0.1 ::1 backend
}
Copy-Item (Join-Path (mkcert -CAROOT) "rootCA.pem") .certs\rootCA.pem

Set-Location $projectRoot
foreach ($name in "VERIFIER_SECRET_KEY", "DJANGO_SECRET_KEY", "POSTGRES_PASSWORD") {
    if (-not (Select-String -Path .env -Pattern "^$name=" -Quiet -ErrorAction SilentlyContinue)) {
        Write-Host "Generating $name in .env..."
        $bytes = New-Object byte[] 32
        [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        Add-Content -Path .env -Value ("$name=" + (($bytes | ForEach-Object { $_.ToString("x2") }) -join ""))
        if ($name -eq "POSTGRES_PASSWORD") {
            Write-Warning "A database created with the old fixed password will refuse it: run 'docker compose down -v' once."
        }
    }
}
$composeFiles = @("-f", "docker-compose.yaml")
if ((docker --version) -match "podman") {
    $composeFiles += @("-f", "docker-compose.podman.yml")
}
Write-Host "Starting Docker Compose..."
# -V: fresh anonymous volumes (.venv, node_modules), owned by the images' non-root users.
docker compose @composeFiles up --build -V

#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT"

install_nss_certutil() {
  if command -v certutil >/dev/null 2>&1; then
    return
  fi

  if command -v apt-get >/dev/null 2>&1; then
    echo "NSS certutil not found. Installing libnss3-tools for Firefox support..."
    sudo apt-get update
    sudo apt-get install -y libnss3-tools
  elif command -v dnf >/dev/null 2>&1; then
    echo "NSS certutil not found. Installing nss-tools for Firefox support..."
    sudo dnf install -y nss-tools
  elif command -v pacman >/dev/null 2>&1; then
    echo "NSS certutil not found. Installing nss for Firefox support..."
    sudo pacman -Sy --noconfirm nss
  else
    echo "NSS certutil is not installed. Chrome/Chromium may still trust the certificate,"
    echo "but Firefox will show it as untrusted. Install libnss3-tools (Debian/Ubuntu),"
    echo "nss-tools (Fedora) or nss (Arch), then run this script again." >&2
  fi
}

if ! command -v mkcert >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "mkcert not found. Installing it with Homebrew..."
    brew install mkcert
  elif command -v apt-get >/dev/null 2>&1; then
    echo "mkcert not found. Installing it with apt..."
    sudo apt-get update
    sudo apt-get install -y mkcert
  else
    echo "mkcert is missing and no supported package manager was found. Install it from https://github.com/FiloSottile/mkcert" >&2
    exit 1
  fi
fi

install_nss_certutil

command -v docker >/dev/null 2>&1 || {
  echo "Docker Desktop is required. Start Docker Desktop and try again." >&2
  exit 1
}

echo "Creating and trusting the local HTTPS certificate..."
cd "$PROJECT_ROOT/backend"
mkdir -p .certs
mkcert -install
mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1 backend
cp "$(mkcert -CAROOT)/rootCA.pem" .certs/rootCA.pem

cd "$PROJECT_ROOT"
for name in VERIFIER_SECRET_KEY DJANGO_SECRET_KEY POSTGRES_PASSWORD; do
  if ! grep -qs "^$name=" .env; then
    echo "Generating $name in .env..."
    echo "$name=$(openssl rand -hex 32)" >> .env
    if [ "$name" = POSTGRES_PASSWORD ]; then
      echo "A database created with the old fixed password will refuse it: run 'docker compose down -v' once." >&2
    fi
  fi
done
COMPOSE_FILES="-f docker-compose.yaml"
if docker --version 2>/dev/null | grep -qi podman; then
  # Rootless Podman: the override maps the host user to the images' default UID 1000.
  COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.podman.yml"
elif [ "$(id -u)" -ne 0 ]; then
  # Docker: build the images' user with the host UID so it can read backend/.certs.
  export KOFRE_UID="$(id -u)"
fi
echo "Starting Docker Compose..."
# -V: fresh anonymous volumes (.venv, node_modules), owned by the images' non-root users.
# Extra arguments go to "docker compose up", e.g. -d to run in the background (CI does).
docker compose $COMPOSE_FILES up --build -V "$@"

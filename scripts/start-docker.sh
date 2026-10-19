#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT"

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

command -v docker >/dev/null 2>&1 || {
  echo "Docker Desktop is required. Start Docker Desktop and try again." >&2
  exit 1
}

echo "Creating and trusting the local HTTPS certificate..."
cd "$PROJECT_ROOT/backend"
mkdir -p .certs
mkcert -install
mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1 backend

cd "$PROJECT_ROOT"
echo "Starting Docker Compose..."
docker compose up --build

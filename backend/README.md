# Kofre backend (Django)

Django + Django REST Framework port of the Kofre banking backend. Local use only.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13.

```sh
cd backend
uv sync
export DJANGO_DEBUG=1   # development defaults; otherwise see .env.example
uv run python manage.py generate_key   # writes .env.d/encryptionKey64.json
uv run python manage.py migrate
# Debian/Ubuntu only: needed for Firefox to trust the local certificate
sudo apt install libnss3-tools
mkcert -install
mkdir .certs
mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1 backend
uv run python manage.py runserver_https 8080
```

The API is then at `https://localhost:8080`. The frontend's HTTPS dev proxy
expects that port.

The field-encryption key can also be given as `SECURITY_ENCRYPTION_KEY_BASE64`
(32 random bytes, base64). See `.env.example`.

With `DJANGO_DEBUG` off (the default) `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`
are required; only debug mode and the test suite fall back to development values.
A production-like configuration passes `check --deploy`:

```sh
DJANGO_SECRET_KEY="$(openssl rand -base64 48)" POSTGRES_PASSWORD=x \
  DJANGO_ALLOWED_HOSTS=localhost uv run python manage.py check --deploy
```

The Docker startup script installs `mkcert` when necessary, then creates and
trusts the local certificate before starting the containers.

## Administrator

Register a user through the app, then:

```sh
uv run python manage.py create_admin <dni>
```

## Tests

```sh
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5432 uv run pytest
```

No secrets are needed: the test suite uses the development defaults.

## Layout

| Path | Contents |
|---|---|
| `kofre/` | Settings and root URLs |
| `common/` | Error type and handler, AES field encryption, validators, ID generator |
| `iam/` | Users, sessions, `/auth`, `/users`, `/admin` |
| `banking/` | Accounts and cards |
| `payments/` | Transfers |
| `tests/` | Contract tests per endpoint |

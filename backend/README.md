# Kofre backend (Django)

Django + Django REST Framework port of the Kofre banking backend. Local use only.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13.

```sh
cd backend
uv sync
uv run python manage.py generate_key   # writes .env.d/encryptionKey64.json
uv run python manage.py migrate
mkcert -install
mkdir .certs
mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1 backend
uv run python manage.py runserver_https 8080
```

The API is then at `https://localhost:8080`. The frontend's HTTPS dev proxy
expects that port.

The field-encryption key can also be given as `SECURITY_ENCRYPTION_KEY_BASE64`
(32 random bytes, base64). See `.env.example`.

The Docker startup script installs `mkcert` when necessary, then creates and
trusts the local certificate before starting the containers.

## Administrator

Register a user through the app, then:

```sh
uv run python manage.py create_admin <dni>
```

## Tests

```sh
uv run pytest
```

## Layout

| Path | Contents |
|---|---|
| `kofre/` | Settings and root URLs |
| `common/` | Error type and handler, AES field encryption, validators, ID generator |
| `iam/` | Users, sessions, `/auth`, `/users`, `/admin` |
| `banking/` | Accounts and cards |
| `payments/` | Transfers |
| `tests/` | Contract tests per endpoint |

# Kofre backend (Django)

Django + Django REST Framework port of the Kofre banking backend. Local use only.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13.

```sh
cd backend
uv sync
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

The Docker startup script installs `mkcert` when necessary, then creates and
trusts the local certificate before starting the containers.

## Roles and administration

Every user has a `role`: `USER` (customer, default), `ADMIN` (full management)
or `AUDITOR` (read-only compliance access). The login response's `user` object
carries both `role` and a boolean `admin` convenience flag.

The first administrator is created after registering a user through the app:

```sh
uv run python manage.py create_admin <dni>
# or, to create an auditor instead:
uv run python manage.py create_admin <dni> --role AUDITOR
```

Administrator endpoints live under `/admin` and are protected by a centralised
policy layer (`iam/permissions.py`); every mutation is written to the audit log.
Administrators can manage users (create, enable/disable, change role, reset
password, delete), accounts (freeze/unfreeze), cards (block/delete), review all
transfers and the audit log, and change system settings (`SESSION_TTL_SECONDS`,
`REGISTRATION_ENABLED`, `TRANSFER_MAX_AMOUNT`, `MAINTENANCE_MODE`,
`LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_SECONDS`). Auditors can only read.

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

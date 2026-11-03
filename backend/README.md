# Kofre backend (Django)

Django + Django REST Framework backend of Kofre: OAuth 2.0 / OpenID Connect
provider, XACML-enforced REST API and field encryption. Local use only.

## Setup

Requires [uv](https://docs.astral.sh/uv/), Python 3.13, PostgreSQL and
[mkcert](https://github.com/FiloSottile/mkcert). With Docker none of this is
needed: see the root [README](../README.md).

```sh
cd backend
uv sync
export DJANGO_DEBUG=1   # development defaults; otherwise see .env.example
export POSTGRES_HOST=127.0.0.1   # default is "db", the Compose service
mkdir -p .env.d && openssl genrsa -out .env.d/oidc.key 2048   # settings load it: needed first
uv run python manage.py generate_key   # writes .env.d/encryptionKey64.json
# Debian/Ubuntu only: needed for Firefox to trust the local certificate
sudo apt install libnss3-tools
mkcert -install
mkdir -p .certs
if command -v openssl >/dev/null 2>&1; then
  openssl req -new -newkey rsa:2048 -nodes \
    -keyout .certs/kofre-bank.key -out .certs/kofre-bank.csr \
    -subj "/C=ES/O=Kofre Bank/OU=Local Development/CN=Kofre Bank Development" \
    -addext "subjectAltName=DNS:kofre-bank.test,DNS:localhost,DNS:backend,IP:127.0.0.1,IP:::1"
  mkcert -csr .certs/kofre-bank.csr -cert-file .certs/localhost.pem
  mv -f .certs/kofre-bank.key .certs/localhost-key.pem
  rm -f .certs/kofre-bank.csr
else
  mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem \
    kofre-bank.test localhost 127.0.0.1 ::1 backend
fi
cp "$(mkcert -CAROOT)/rootCA.pem" .certs/rootCA.pem
uv run python manage.py migrate
uv run python manage.py create_oauth_client
uv run python manage.py runserver_https 8080
```

The API is then at `https://localhost:8080`. The frontend's HTTPS dev proxy
expects that port. Adding a card also needs the verifier service (see the root
README).

The OIDC key can also be given as `OIDC_RSA_PRIVATE_KEY`, the field-encryption
key as `SECURITY_ENCRYPTION_KEY_BASE64` (32 random bytes, base64). See
`.env.example`.

With `DJANGO_DEBUG` off (the default) `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`
are required; only debug mode and the test suite fall back to development values.
A production-like configuration passes `check --deploy`:

```sh
DJANGO_SECRET_KEY="$(openssl rand -base64 48)" POSTGRES_PASSWORD=x \
  DJANGO_ALLOWED_HOSTS=localhost uv run python manage.py check --deploy
```

## Field encryption

DNI, email, phone number, PAN and card PIN are stored as AES-256-GCM
`v1:<key id>:<nonce>:<ciphertext>`, bound to `<table>.<column>.<row id>` as
associated data. DNI, phone and PAN lookups use an HMAC-SHA256 blind index under a
separate key. `generate_key --rotate` adds a new current key; old values still
decrypt. Passwords and the user PIN are not encrypted but hashed with Argon2id.

## Roles

Register a user through the app, then:

```sh
uv run python manage.py set_role <dni> admin   # or auditor, operations, or customer
```

`create_admin <dni>` is the same as `set_role <dni> admin`.

For demo users without signing up, `seed_users` creates two customers, an admin
and an auditor, and gives each customer a debit card (see "Test data" in the root
README). It prints a random password, PIN and card PIN once, or takes
`--password`, `--pin` and `--card-pin`.

## Tests

The tests need PostgreSQL and `.env.d/oidc.key`; they set their own encryption
key and fall back to the development secret key and database password
(`password`, user `user`). With the throwaway container from the root README:

```sh
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5432 uv run pytest
```

## Layout

| Path | Contents |
|---|---|
| `kofre/` | Settings and root URLs |
| `common/` | Errors, field encryption, lockout, CSP, validators, `runserver_https` |
| `iam/` | Users, OAuth login page and client, `/auth`, `/users`, `/admin` |
| `authz/` | XACML policy, PDP, PIP, PEP and audit trail |
| `banking/` | Accounts and cards |
| `payments/` | Transfers |
| `tests/` | Contract tests per endpoint |

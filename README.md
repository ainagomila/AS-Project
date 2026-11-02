# AS-Project

[![CI](https://github.com/ainagomila/AS-Project/actions/workflows/ci.yml/badge.svg)](https://github.com/ainagomila/AS-Project/actions/workflows/ci.yml)

Kofre: a small online banking web application (registration and login,
accounts, transfers, cards, profile, back office) built for the UPC Application
Security lab with security by design, following OWASP ASVS 5.0. It started as a
Django port of an older Spring Boot app whose weaknesses were kept on purpose,
and has since been secured with the six lab features:

| Feature | In short |
|---|---|
| Password protection | Argon2id hashes for passwords and user PINs |
| Server certificate | HTTPS everywhere in the browser, local mkcert CA |
| Authentication | OAuth 2.0 / OpenID Connect, Authorization Code with PKCE |
| Database encryption | AES-256-GCM for DNI, email, phone, card PAN and card PIN; blind indexes for lookups |
| Automated vulnerability checking | pip-audit, npm audit, Bandit, Semgrep, gitleaks and Trivy in CI |
| Privacy rules | XACML 3.0 policy, roles `customer`, `admin`, `auditor`, audit trail |

- [`docs/vulnerability-inventory.md`](docs/vulnerability-inventory.md): every
  weakness of the baseline by ID and, in section 7, its current status.
- [`docs/asvs-mapping.md`](docs/asvs-mapping.md): ASVS 5.0 requirements, where
  they are met and the known gaps.

**Run it locally only. Do not deploy it or put real data in it.**

## Run
The scripts use [mkcert](https://github.com/FiloSottile/mkcert) to create and
trust a local development certificate on the host before Docker starts.

To automate certificate setup and start Docker on Windows, run:

```powershell
.\scripts\start-docker.ps1
```

On macOS or Linux, run:

```sh
./scripts/start-docker.sh
```

These scripts install `mkcert` with the operating system's package manager
when it is missing, run `mkcert -install`, create the certificate on the host,
copy mkcert's root certificate (`rootCA.pem`) next to it, and then start Docker
Compose. The package manager may ask for administrator approval. Then open
`https://localhost:5173`.

The scripts also generate the secrets Docker Compose needs into a gitignored
`.env` at the repository root: `VERIFIER_SECRET_KEY`, `DJANGO_SECRET_KEY` and
`POSTGRES_PASSWORD`. The database password used to be fixed, so if you already
have a Kofre database volume, run `docker compose down -v` once (this erases the
local data). The backend runs with `DEBUG` off; set `DJANGO_DEBUG=1` in `.env`
for Django's debug pages.

The backend and frontend containers run as an unprivileged user whose UID must be
able to read the bind-mounted certificate and keys in `backend/.certs`. With
Docker, `start-docker.sh` builds that user with your UID (`KOFRE_UID`, default
1000). With rootless Podman it adds `docker-compose.podman.yml`, which maps your
user to UID 1000 instead.

`rootCA.pem` is what lets the frontend's dev proxy verify the backend's
certificate. When the backend container starts it creates the OIDC signing key
and the field-encryption keyring in `backend/.env.d/` if they are missing, applies
the migrations and creates the OAuth client `kofre-web`, so there is nothing else
to set up. Keep `backend/.env.d/`: without the keyring the encrypted data in the
database cannot be read (then `docker compose down -v` starts over).

## Run (manually without Docker)

Backend (needs [uv](https://docs.astral.sh/uv/) and Python 3.13):

```sh
cd backend
uv sync
export DJANGO_DEBUG=1   # or set DJANGO_SECRET_KEY and POSTGRES_PASSWORD
mkdir -p .env.d && openssl genrsa -out .env.d/oidc.key 2048   # needed by every manage.py command
uv run python manage.py generate_key
mkcert -install
mkdir .certs
mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1 backend
cp "$(mkcert -CAROOT)/rootCA.pem" .certs/rootCA.pem
uv run python manage.py migrate
uv run python manage.py create_oauth_client
uv run python manage.py runserver_https 8080
```

In PowerShell the copy is
`Copy-Item (Join-Path (mkcert -CAROOT) "rootCA.pem") .certs\rootCA.pem`.
Never copy `rootCA-key.pem`. If your Vue app is not served from
`https://localhost:5173`, set `FRONTEND_URL` before running `create_oauth_client`.
The database is read from `POSTGRES_HOST` (default `db`), `POSTGRES_PORT`,
`POSTGRES_DB`, `POSTGRES_USER` and `POSTGRES_PASSWORD`; see `backend/.env.example`.

Adding a card needs the card verifier on port 5678 (the backend's `VERIFIER_URL`):

```sh
cd verifier-backend
SECRET_KEY="$(openssl rand -hex 32)" uv run fastapi run app/main.py --port 5678
```

Frontend (needs Node 20.19+ or 22.12+):

```sh
cd frontend
npm install
npm run dev
```

Open `https://localhost:5173`. The certificate is stored in `backend/.certs/`
and trusted by `mkcert`. The backend is available at
`https://localhost:8080`.

## Signing in

Login uses OAuth 2.0 (Authorization Code with PKCE) through django-oauth-toolkit.
The Vue app redirects to the backend's login page (`/accounts/login/`), receives a
code at `/callback` and exchanges it for a 5-minute access token. Tokens are kept
in memory only, so reloading the page signs you in again through the backend.
`/signup` and "Forgot password?" stay in Vue.

Sessions last 5 minutes: a minute before expiry the app offers to extend (5 more
minutes) and otherwise signs out through `/o/logout/`, which revokes the tokens.
Without `DJANGO_DEBUG=1` the backend refuses to start unless `DJANGO_SECRET_KEY`
and `POSTGRES_PASSWORD` are set. Details are in section 7 of the
[inventory](docs/vulnerability-inventory.md).

## Roles and privacy rules

Access is decided by an XACML 3.0 policy,
[`backend/authz/policies/kofre-policy.xml`](backend/authz/policies/kofre-policy.xml),
evaluated for every API request (details in section 7 of the
[inventory](docs/vulnerability-inventory.md)). There are three roles:

| Role | Can do |
|---|---|
| `customer` (default) | Only their own profile, accounts, cards and transfers. |
| `admin` | Create customers, list customer identities, reset customer passwords, delete customers, and enable or disable customers. The web API cannot provision staff roles. Never sees balances or transfers, and cannot modify staff or themselves. |
| `operations` | List accounts and cards using masked identifiers, and activate, freeze or close them with a mandatory reason. Cannot see balances, transfers or full card data. |
| `auditor` | Read any user's accounts and transfers with personal data masked, and read the audit trail. Changes nothing. |

To give a role, register the user in the app and run, in `backend/`:

```sh
uv run python manage.py set_role <dni> admin     # or auditor, or customer
uv run python manage.py set_role <dni> operations # account/card operations
```

(`create_admin <dni>` still works.) With Docker:
`docker compose exec backend uv run python manage.py set_role <dni> auditor`.
The back office is the shield icon in the header.

## Test data

Made-up values that pass both the frontend's and the backend's validation.

**Seeded users.** To skip sign-up, create two customers, an admin and an
auditor, each with the usual 100 EUR "Kofre" account:

```sh
docker compose exec backend uv run python manage.py seed_users
```

| DNI | Role |
|---|---|
| `10000001S` | customer |
| `10000002Q` | customer |
| `10000003V` | admin |
| `10000004H` | auditor |

No credentials are hard-coded: the command prints a random password and user
PIN once (shared by the four users), or takes `--password` and `--pin`. Users
that already exist are left unchanged, so it is safe to run again.

**Users.** The DNI needs the right control letter. Sign-up also requires an
adult birthdate and a Spanish mobile number (`+34` and 9 digits). Each DNI and
phone can be registered once; registering a taken one answers the same message
but creates nothing.

| DNI | Phone |
|---|---|
| `11111111H` | `+34 600 111 111` |
| `22222222J` | `+34 600 222 222` |
| `33333333P` | `+34 600 333 333` |
| `44444444A` | `+34 600 444 444` |
| `55555555K` | `+34 600 555 555` |
| `12345678Z` | `+34 600 123 456` |

A password that meets the rules (8+ characters, upper, lower, digit, special):
`Secret_123`. The user PIN is any 6 digits, for example `123456`.

**Accounts.** Spanish IBANs with valid check digits, for "Add account". Each
IBAN can be added once. Every new user also gets a "Kofre" account with a
random IBAN and 100 EUR, which is the one to use as a transfer destination.

| IBAN |
|---|
| `ES9121000418450200051332` |
| `ES6800491500042110123456` |
| `ES8001822370440201234567` |
| `ES9120385778966000123456` |
| `ES2000810200280001234567` |

**Cards.** 16 digits that pass the Luhn check; these are the usual test
numbers. Each can be added once. Use a 4-digit card PIN and an expiry date in
the future. The CVV is not free: the verifier derives it from the PAN and the
expiry date (`MM/YY`) with its secret key, as the issuing bank would. Get it with:

```sh
docker compose exec verifier python -c 'import hmac, os, sys; pan, exp = sys.argv[1:]; tag = hmac.new(os.environ["SECRET_KEY"].encode(), f"{pan}E{exp}".encode(), "sha256").digest(); print("%03d" % (int.from_bytes(tag, "big") % 1000))' 4111111111111111 12/28
```

(Without Docker, run the same `python3 -c ...` with `SECRET_KEY` set to the
verifier's key.)

| Card number | Card PIN |
|---|---|
| `4111 1111 1111 1111` | `1234` |
| `5500 0000 0000 0004` | `4321` |
| `4000 0000 0000 0002` | `0000` |
| `5105 1051 0510 5100` | `9999` |

## Tests

Backend tests need PostgreSQL and the OIDC key (the settings load it); they bring
their own encryption key and fall back to the development `DJANGO_SECRET_KEY` and
`POSTGRES_PASSWORD` (`password`). The Compose database does not publish a port, so
start a throwaway one:

```sh
docker run -d --name kofre-test-db -p 127.0.0.1:5432:5432 \
  -e POSTGRES_USER=user -e POSTGRES_PASSWORD=password -e POSTGRES_DB=kofredb postgres:18
cd backend
mkdir -p .env.d && [ -f .env.d/oidc.key ] || openssl genrsa -out .env.d/oidc.key 2048
POSTGRES_HOST=127.0.0.1 uv run pytest   # POSTGRES_PORT=... if 5432 is taken
```

Frontend:

```sh
cd frontend && npm ci
npm run lint
npx vitest run --exclude 'src/test/integration/**' --exclude 'src/test/e2e/**'   # unit and component tests
npm run test:e2e:local                                                         # browser tests
```

The integration (`src/test/integration`) and browser tests talk to a running
stack on `https://localhost:5173` and `https://localhost:8080` and leave their
test users in its database.

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs on every push to
`main` and every pull request: backend tests against Postgres, frontend lint and
unit tests (Node 22), and the security scanner (`docker-compose.security.yml`),
which fails on CRITICAL or HIGH findings.

## Docs

- [`docs/specs/2026-10-09-django-baseline-design.md`](docs/specs/2026-10-09-django-baseline-design.md): what was ported and why
- [`docs/specs/2026-10-09-django-baseline-plan.md`](docs/specs/2026-10-09-django-baseline-plan.md): how the port was carried out
- [`docs/vulnerability-inventory.md`](docs/vulnerability-inventory.md): weaknesses of the baseline and their current status
- [`docs/asvs-mapping.md`](docs/asvs-mapping.md): OWASP ASVS 5.0 mapping
- [`backend/README.md`](backend/README.md): backend details

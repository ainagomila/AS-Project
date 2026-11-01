# AS-Project

Kofre: a small online banking web application used as the Application Security
course project. This repository holds the **vulnerable baseline**: a Django port
of an earlier Spring Boot backend, cut down to registration and login, accounts,
transfers, cards, profile management and an administrator role, together with
the Vue frontend.

The baseline is intentionally not hardened. Known weaknesses are listed in
[`docs/vulnerability-inventory.md`](docs/vulnerability-inventory.md); the
security features are added on top of it on separate branches.

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
Compose. The package manager may ask for administrator approval.

`rootCA.pem` is what lets the frontend's dev proxy verify the backend's
certificate. When the backend container starts it also generates the OIDC signing
key (if missing), applies the migrations and creates the OAuth client `kofre-web`,
so there is nothing else to set up. If you update from an older version of the
branch, start with `docker compose up --build` (or run the script again) so the
frontend image gets the new `oidc-client-ts` dependency.

## Run (manually without Docker)

Backend (needs [uv](https://docs.astral.sh/uv/) and Python 3.13):

```sh
cd backend
uv sync
uv run python manage.py generate_key
mkdir -p .env.d && openssl genrsa -out .env.d/oidc.key 2048
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
Outside development set `DJANGO_SECRET_KEY`. Details are in section 7 of the
[inventory](docs/vulnerability-inventory.md).

## Roles and privacy rules

Access is decided by an XACML 3.0 policy,
[`backend/authz/policies/kofre-policy.xml`](backend/authz/policies/kofre-policy.xml),
evaluated for every API request (details in section 8 of the
[inventory](docs/vulnerability-inventory.md)). There are three roles:

| Role | Can do |
|---|---|
| `customer` (default) | Only their own profile, accounts, cards and transfers. |
| `admin` | List users and enable or disable customers. Never sees balances or transfers, and cannot disable staff or themselves. |
| `auditor` | Read any user's accounts and transfers with personal data masked, and read the audit trail. Changes nothing. |

To give a role, register the user in the app and run, in `backend/`:

```sh
uv run python manage.py set_role <dni> admin     # or auditor, or customer
```

(`create_admin <dni>` still works.) With Docker:
`docker compose exec backend uv run python manage.py set_role <dni> auditor`.
The back office is the shield icon in the header.

## Test data

Made-up values that pass both the frontend's and the backend's validation.

**Users.** The DNI needs the right control letter. Sign-up also requires an
adult birthdate and a Spanish mobile number (`+34` and 9 digits), and each DNI
and phone can be registered once.

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

**Cards.** Any 16 digits are accepted (there is no Luhn check); these are the
usual test numbers. Each can be added once. Use a 3-digit CVV, a 4-digit card
PIN and an expiry date in the future.

| Card number | CVV | Card PIN |
|---|---|---|
| `4111 1111 1111 1111` | `123` | `1234` |
| `5500 0000 0000 0004` | `456` | `4321` |
| `4000 0000 0000 0002` | `789` | `0000` |
| `5105 1051 0510 5100` | `321` | `9999` |

## Tests

```sh
cd backend && uv run pytest          # API contract tests
cd frontend && npx vitest run        # unit, component and integration tests
cd frontend && npx playwright test   # browser tests
```

The frontend integration and browser tests talk to a running backend on
`https://localhost:8080` and leave their test users in its database. They sign in
through OAuth, so run them with `E2E_BASE_URL=https://localhost:5173`
(`npm run test:e2e:local` does it).

## Docs

- [`docs/specs/2026-10-09-django-baseline-design.md`](docs/specs/2026-10-09-django-baseline-design.md): what was ported and why
- [`docs/specs/2026-10-09-django-baseline-plan.md`](docs/specs/2026-10-09-django-baseline-plan.md): how the port was carried out
- [`docs/vulnerability-inventory.md`](docs/vulnerability-inventory.md): weaknesses present in the baseline
- [`backend/README.md`](backend/README.md): backend details

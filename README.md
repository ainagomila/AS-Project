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

Backend (needs [uv](https://docs.astral.sh/uv/) and Python 3.13):

```sh
cd backend
uv sync
uv run python manage.py generate_key
uv run python manage.py migrate
uv run python manage.py runserver 8080
```

Frontend (needs Node 20.19+ or 22.12+):

```sh
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to the backend on
port 8080.

To get an administrator, register a user in the app and run
`uv run python manage.py create_admin <dni>` in `backend/`, then log in again.

## Tests

```sh
cd backend && uv run pytest          # API contract tests
cd frontend && npx vitest run        # unit, component and integration tests
cd frontend && npx playwright test   # browser tests
```

The frontend integration and browser tests talk to a running backend on
`http://localhost:8080` and leave their test users in its database.

## Docs

- [`docs/specs/2026-10-09-django-baseline-design.md`](docs/specs/2026-10-09-django-baseline-design.md): what was ported and why
- [`docs/specs/2026-10-09-django-baseline-plan.md`](docs/specs/2026-10-09-django-baseline-plan.md): how the port was carried out
- [`docs/vulnerability-inventory.md`](docs/vulnerability-inventory.md): weaknesses present in the baseline
- [`backend/README.md`](backend/README.md): backend details

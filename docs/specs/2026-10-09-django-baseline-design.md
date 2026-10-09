# Kofre → Django baseline: design

Date: 2026-10-09
Status: awaiting team review

## 1. Purpose

Port the Kofre banking backend (Spring Boot + Firestore) to Django + Django REST
Framework, cut down to what the Application Security lab brief asks for, and keep
the existing Vue frontend working against it.

The result is the **vulnerable baseline** for the course project. It is a
faithful port: weaknesses in the original are carried over unchanged, nothing is
planted on purpose, and whatever Django fixes by default stays fixed. After the
port, an inventory of the remaining weaknesses is written and the team decides
whether more are needed. The six security features in the brief are implemented
later, on separate branches, starting from the tagged baseline.

Source code being ported: `~/projectes/kofre/Kofre-backend/Kofre-backend-dev`
and `~/projectes/kofre/Kofre-frontend/Kofre-frontend-main`. Where the docs and
the Java controllers disagree, the controllers are the source of truth.

## 2. Scope

### Kept

| Area | Method and route |
|---|---|
| Auth | `POST /auth/register` |
| | `POST /auth/login` |
| | `POST /auth/logout` |
| | `POST /auth/validate` |
| | `GET /auth/exists/{dni}` |
| | `POST /auth/reset-password` |
| Users | `GET /users` |
| | `GET /users/{dni}` |
| | `PATCH /users/{dni}` |
| | `DELETE /users/{dni}` |
| | `POST /users/{dni}/security/verify-pin` |
| | `POST /users/{dni}/security/verify-password` |
| Accounts | `GET /users/{dni}/accounts` |
| | `POST /users/{dni}/accounts` |
| | `GET /users/{dni}/accounts/{iban}` |
| | `PATCH /users/{dni}/accounts/{iban}` |
| | `DELETE /users/{dni}/accounts/{iban}` |
| Transfers | `GET /users/{dni}/accounts/{iban}/transfers` |
| | `POST /users/{dni}/accounts/{iban}/transfers` |
| Cards | `GET /users/{dni}/cards` |
| | `GET /users/{dni}/accounts/{iban}/cards` |
| | `POST /users/{dni}/accounts/{iban}/cards` |
| | `GET /users/{dni}/accounts/{iban}/cards/{pan}` |
| | `PATCH /users/{dni}/accounts/{iban}/cards/{pan}` |
| | `DELETE /users/{dni}/accounts/{iban}/cards/{pan}` |
| | `POST /users/{dni}/accounts/{iban}/cards/{pan}/security/verify-card` |

Request bodies, response bodies, status codes and error codes for these routes
match the Java implementation, including the Catalan error messages.

### Dropped

Tricounts, expenses, tricount invitations, Bizum, contacts and contact requests,
dashboard analytics, savings goal. The bank and country catalogues are dropped
unless account or card creation turns out to depend on them; if it does, the
needed values become constants in code.

Also dropped: Terraform, Cloud Build, Firebase config, Dockerfiles, the GitHub
workflows, Swagger UI and the actuator endpoints. The app runs locally only.

### New (required by the brief, absent from the original)

An administrator role.

| Method and route | Behaviour |
|---|---|
| `GET /admin/users` | List all users, including `active` and `admin` flags |
| `GET /admin/users/{dni}/accounts` | List any user's accounts |
| `GET /admin/users/{dni}/accounts/{iban}/transfers` | List any account's transfers |
| `PATCH /admin/users/{dni}` | Body `{"active": true|false}`; enable or disable a user |

- A disabled user cannot log in and their existing tokens are rejected, both
  with `403` and error code `USER_DISABLED`.
- The first admin is created with a management command:
  `uv run python manage.py create_admin <dni>`, which sets `is_admin` on an
  existing user.
- Each admin view checks `is_admin` inline and returns `403` with code
  `FORBIDDEN` otherwise. There is no shared policy layer in the baseline; that
  is the job of the later XACML-style feature.
- Django's own admin site is not installed.

## 3. Repository layout

```
AS-Project/
  backend/
    pyproject.toml
    uv.lock
    manage.py
    kofre/            # project: settings, urls, error handler
    iam/              # users, sessions, auth, admin endpoints
    banking/          # accounts, cards
    payments/         # transfers
    common/           # AES field encryption, IBAN/DNI validators, error types
    tests/
  frontend/           # trimmed copy of the Vue app
  docs/
    specs/
    vulnerability-inventory.md   # written after the port
```

Each app has `models.py`, `serializers.py`, `views.py`, `urls.py` and a
`services.py` that holds the business rules. Views parse the request, call one
service function and shape the response.

## 4. Stack

- Python 3.13, Django 5.2 LTS, Django REST Framework
- SQLite
- `cryptography` (AES-GCM), `django-cors-headers`, an IBAN validation library
- pytest + pytest-django
- uv with `pyproject.toml` and a committed `uv.lock`
- The dev server listens on port 8080, so the frontend's dev proxy is unchanged.

## 5. Data model

| Model | Fields | Notes |
|---|---|---|
| `User` | `id`, `dni` (unique), `name`, `email`, `phone_prefix`, `phone_number`, `birthdate`, `gender`, `password_*`, `pin_*`, `is_admin`, `is_active` | Plain `models.Model`. Django's auth app is not used. |
| `Session` | `token` (UUID4, unique), `user`, `expires_at` | 24 h lifetime. Several per user. Expired rows purged at login. |
| `Account` | `id`, `iban` (unique), `name`, `bank`, `balance`, `currency`, `user` | |
| `Card` | `id`, `pan`, `cvv`, `expire_date`, `alias`, `bank`, `type`, `status`, `pin_*`, `account` | `type`: DEBIT, CREDIT. `status`: ACTIVE, FREEZED, DEAD. |
| `Payment` | `id`, `emitter_iban`, `receiver_iban`, `amount`, `currency`, `concept`, `categories`, `payment_date`, `status`, `failure_reason` | Bank transfers only. Categories as in the original minus `TRICOUNT`. |

`password_*` and `pin_*` are three columns each (`iv`, `ciphertext`, `tag`),
produced by reversible AES-GCM exactly as the original `EncryptionService` does.
The key is read from a local key file or from an environment variable.

Validation rules (DNI, email, phone, password complexity, PIN, IBAN, CVV, PAN,
positive amounts, matching currencies, sufficient funds) are ported from the
Java value objects.

## 6. Authentication and authorisation

- `POST /auth/login` decrypts the stored password, compares it to the submitted
  one, creates a `Session` and returns `{token, user}`.
- One DRF authentication class reproduces `AuthInterceptor`:
  - requires `Authorization: Bearer <token>`;
  - if the route has a `{dni}`, the token must be a live session of that user;
  - if it has none, any live token is accepted.
- The class is applied to `/users/**` and `/admin/**`. `/auth/**` is public.
- Operations that require the user PIN in the original (delete user, delete
  account, transfers, profile changes) still require it.
- CORS allows the configured origins with credentials, as in `WebConfig`.
- Django's session, CSRF and auth middleware are not part of the API path.

## 7. Behaviour carried over as-is

These are known weaknesses of the original. They are kept deliberately and must
not be "fixed" during the port.

- Password and user PIN stored with reversible encryption, compared in plaintext.
- Card PIN encrypted; PAN and CVV stored in clear.
- Home-made UUID bearer tokens with a 24 h lifetime; frontend keeps the token in
  `localStorage`.
- `POST /auth/reset-password` needs only DNI + PIN.
- `GET /auth/exists/{dni}` and distinct login errors (`USER_NOT_FOUND` vs
  `INVALID_CREDENTIALS`) allow user enumeration.
- `GET /users` returns every user to any authenticated caller.
- `POST /users/{dni}/accounts` accepts a client-chosen starting balance.
- Transfers debit, credit and record the payment as three separate writes with
  no database transaction or row locking.
- No rate limiting or lockout on login, PIN or card verification.
- Plain HTTP.

## 8. Error handling

One DRF exception handler turns service errors, validation errors and unhandled
exceptions into the existing body:

```json
{ "code": "INVALID_PIN", "message": "El PIN és incorrecte!", "metadata": {} }
```

Service functions raise a single `AppError(code, message, status)` type. The
code-to-status mapping is ported from `ProblemMapper` and
`GlobalExceptionHandler`.

## 9. Frontend

- Copy the Vue app into `frontend/`.
- Remove the views, stores, services, routes, components and tests for tricount,
  groups, social, Bizum, contacts and the dashboard analytics. The dashboard
  view keeps accounts and cards.
- Remove calls to dropped endpoints from `userService.js`.
- Add one admin view (user list with enable/disable, drill-down to accounts and
  transfers), visible only when the logged-in user is an admin. The login
  response's `user` object gains an `admin` boolean for this.
- No other behaviour changes; token handling stays as it is.

## 10. Testing

- pytest contract tests for every kept and new endpoint: success status and
  JSON shape, plus the main error cases and their codes. Derived from
  `docs/API_SPEC.md`, `api-tests.http` and the Java controller tests.
- Unit tests for the ported validators and the AES round trip.
- Frontend unit tests and Playwright specs trimmed to the kept views and run
  against the Django server as the end-to-end check.
- No test asserts that a weakness exists. Weaknesses live in the inventory.

## 11. Vulnerability inventory

Written once the port passes its tests, before tagging.

`docs/vulnerability-inventory.md` contains:

1. **Remaining weaknesses**: location in the Django/Vue code, how to reproduce,
   CWE and OWASP Top 10 category, and which lab feature it maps to (password
   protection, server certificate, OAuth 2.0, partial database encryption,
   automated vulnerability checking, XACML-style privacy rules) or "other".
2. **Fixed by the port**: weaknesses of the original that disappeared because of
   Django or SQLite defaults, with a short explanation.

The team then decides whether to plant anything extra. Planting is out of scope
for this spec.

## 12. Git workflow

- Port work happens on `port/django-baseline`, merged to `main` when the team
  accepts it.
- The accepted commit is tagged `baseline-vulnerable`.
- Each security feature or fix gets its own branch and pull request from that
  tag onwards, so every diff is usable in the report.

## 13. Order of work

1. Scaffold `backend/` (uv, settings, error handler, `common/`).
2. `iam`: models, auth endpoints, user endpoints, authentication class.
3. `banking`: accounts, then cards.
4. `payments`: transfers.
5. Admin endpoints and the `create_admin` command.
6. Frontend: trim, rewire, admin view.
7. End-to-end run, then the vulnerability inventory.

## 14. Out of scope

- Implementing any of the six security features.
- Planting additional vulnerabilities.
- Deployment, containers, CI.
- Migrating data from Firestore.

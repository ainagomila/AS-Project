# Kofre → Django baseline: implementation plan

Implements `2026-10-09-django-baseline-design.md`. Work happens on
`port/django-baseline`.

Paths under **Java source** are relative to
`~/projectes/kofre/Kofre-backend/Kofre-backend-dev/backend/src/main/java/com/kofre/`.
Frontend source is `~/projectes/kofre/Kofre-frontend/Kofre-frontend-main/frontend/`.

## Rules for every task

- **Port, do not improve.** If the Java code does something unsafe, the Python
  code does the same thing. Section 7 of the design lists the known cases; any
  new one found while porting is noted in `docs/port-notes.md` for the
  inventory, not fixed.
- **Controllers and DTO records are the contract**, not `API_SPEC.md`. The spec
  is out of date in places (for example it shows `pin` inside the user object;
  check `UserResponse.java` before deciding).
- Each task ends with its tests passing: `cd backend && uv run pytest`.
- One commit per task.

## Task 1: backend scaffold

Create:
- `backend/pyproject.toml` (Python 3.13; django 5.2, djangorestframework,
  django-cors-headers, cryptography, schwifty for IBAN; dev group: pytest,
  pytest-django), `backend/uv.lock`
- `backend/manage.py`, `backend/kofre/{settings,urls,wsgi,asgi}.py`
- `backend/common/errors.py`: `ErrorCode` enum, `AppError(code, message,
  metadata={})`, `STATUS_BY_CODE`, DRF `exception_handler`
- `backend/.env.example`, `.gitignore` (venv, `db.sqlite3`, key file, `.env`)
- `backend/README.md`: install, migrate, run on port 8080, run tests

Details:
- `INSTALLED_APPS`: `rest_framework`, `corsheaders`, `common`, `iam`, `banking`,
  `payments`. No `django.contrib.admin`, `auth`, `sessions`.
- `MIDDLEWARE`: CORS and common middleware only. No CSRF, session or auth
  middleware.
- `REST_FRAMEWORK`: JSON renderer and parser only, no default authentication or
  permission classes, `EXCEPTION_HANDLER` set to the custom one,
  `UNAUTHENTICATED_USER = None`.
- CORS: allowed origins from `CORS_ALLOWED_ORIGINS` (default
  `http://localhost:5173`), credentials allowed, all headers. Source:
  `config/WebConfig.java`.
- `STATUS_BY_CODE` copied from `application/problemMappers/ProblemMapper.java`,
  minus the tricount, catalogue and contact codes. Note `UNAUTHORIZED` maps to
  **403** there, while the auth interceptor itself answers a bare **401** with
  no body. Keep both behaviours.
- Unhandled exceptions and DRF validation errors: follow
  `config/GlobalExceptionHandler.java`.

Tests: handler returns `{code, message, metadata}` with the mapped status for a
sample of codes; unknown exception gives 500 `INTERNAL_ERROR`.

## Task 2: common building blocks

Create `backend/common/crypto.py` and `backend/common/validators.py`.

- `crypto.py`: `encrypt(plain) -> (iv, ciphertext, tag)` and `decrypt(...)`,
  AES-GCM. Key loading, key size, IV size and encodings follow
  `infra/shared/EncryptionService.java` and `infra/EncryptionConfig.java`
  (key file or `SECURITY_ENCRYPTION_KEY_BASE64`). A `generate_key` management
  command writes a local key file for development.
- `validators.py`: one function per Java value object, raising `AppError` with
  the same code and message.

| Validator | Java source |
|---|---|
| DNI | `domain/iam/valueobjects/Dni.java` |
| Email | `domain/iam/valueobjects/Email.java` |
| Password rules | `domain/iam/valueobjects/Password.java` |
| User PIN | `domain/iam/valueobjects/UserPin.java` |
| Birthdate, gender | `domain/iam/valueobjects/{Birthdate,Gender}.java` |
| Phone | `domain/shared/valueobjects/PhoneNumber.java`, `splitPhone` in `AuthCommandService.java` |
| IBAN | `domain/banking/valueobjects/Iban.java` |
| PAN, CVV, card PIN | `domain/banking/valueobjects/{Pan,Cvv,Pin}.java` |
| Money, currency | `domain/shared/valueobjects/Money.java`, `domain/shared/enums/Currency.java` |

Tests: port the cases from the matching Java tests under
`backend/src/test/java/com/kofre/domain/`; AES round trip; wrong key fails.

## Task 3: iam models and auth endpoints

Create `backend/iam/{models,serializers,services,views,urls,authentication}.py`
and the first migration.

- Models `User` and `Session` as in design section 5. User id generation follows
  `domain/iam/factories/UserFactory.java` and `domain/shared/id/IdGenerator.java`.
- `services.py`: `register`, `login`, `logout`, `validate`, `exists`,
  `reset_password`. Source: `application/services/iam/AuthCommandService.java`
  and `application/controller/iam/AuthCommandController.java`. Session rules
  (24 h, purge expired on login, several per user) from
  `domain/iam/entities/User.java`.
- Register also creates the initial zero-balance "Kofre" account with a random
  Spanish IBAN. The `Account` model does not exist yet, so add a minimal
  `banking/models.py` with `Account` in this task.
- `authentication.py`: `KofreTokenAuthentication`, behaviour copied from
  `config/AuthInterceptor.java`: OPTIONS passes; missing or malformed header is
  a bare 401; with `{dni}` in the route the token must be a live session of that
  user; without it any live token passes. Sets `request.user` to the token's
  owner.
- New behaviour from the design: a user with `is_active = False` gets 403
  `USER_DISABLED` at login and on any authenticated request.

Tests: each endpoint's success case and listed errors; token for user A on a
`/users/{B}` route gives 401; expired token gives 401; disabled user gives 403.

## Task 4: user endpoints

Add to `iam`: `GET /users`, `GET/PATCH/DELETE /users/{dni}`, `verify-pin`,
`verify-password`.

Source: `application/controller/iam/{UserQueryController,UserCommandController}.java`,
`application/services/iam/{UserQueryService,UserCommandService}.java`, request
and response records under `application/dtos/iam/`.

- `PATCH` accepts email, phone, password or new PIN, each requiring the current
  PIN; reproduce the exact branching and error codes, including
  `PASSWORD_ALREADY_EXISTS`.
- Savings-goal routes are not ported.
- Check what deleting a user does to their accounts, cards and sessions in the
  Java code and do the same.

Tests: one per PATCH variant, wrong PIN gives 422 `INVALID_PIN`, delete, verify
endpoints, `GET /users` shape.

## Task 5: accounts

Complete `banking`: serializers, services, views, urls for the five account
routes.

Source: `application/controller/banking/Account{Query,Command}Controller.java`,
`application/services/banking/Account{Query,Command}Service.java`,
`domain/banking/entities/Account.java`, `domain/banking/factories/AccountFactory.java`.

- Create takes `iban`, `name`, `bank`, `balance`, `currency` from the client.
- Rename needs no PIN; delete needs the PIN.
- Ownership check as in `getOwnedAccount`.
- `balance` serialises as a JSON number, not a string.

Tests: CRUD, duplicate IBAN 409, invalid IBAN 400, negative balance 400,
another user's account gives the `UNAUTHORIZED` error, delete with wrong PIN.

## Task 6: cards

Add `Card` model, migration and the seven card routes.

Source: `application/controller/banking/Card{Query,Command}Controller.java`,
`application/services/banking/Card{Query,Command}Service.java`,
`domain/banking/entities/Card.java`, `infra/banking/mappers/CardMapper.java`
(which fields are encrypted), `config/BankingConfig.java`.

- Card PIN encrypted with `common.crypto`; PAN and CVV plain columns.
- `GET .../cards/{pan}` response shape (object or one-element array): follow the
  controller.
- `PATCH` handles alias and status; check how the controller maps the incoming
  status strings to `ACTIVE/FREEZED/DEAD`.
- `verify-card` takes the user PIN and returns PAN, expiry, CVV and card PIN.
- If `BankingConfig` or the services depend on the bank catalogue, replace it
  with a constant list in `banking/constants.py`.

Tests: create, both lists, detail, alias, status, delete, verify-card success
and wrong PIN, duplicate PAN 409, format errors.

## Task 7: transfers

Create `backend/payments/{models,serializers,services,views,urls}.py`.

Source: `application/controller/payments/transfers/*.java`,
`application/services/payments/{TransferCommandService,TransfersQueryService,AuxPaymentService,SortSpec}.java`,
`domain/payments/**`, `infra/payments/mappers/PaymentMapper.java`.

- `POST`: validations and their order as in `addTransfer`; then debit source,
  credit destination and save the payment as three separate saves, with no
  `transaction.atomic` and no `select_for_update`.
- Destination must be an existing Kofre account.
- `GET`: response `{"transfers": [...]}` with `title`, `date`, `amount`
  (negative for outgoing), `currency`, `categories`; query params `q`,
  `onlyExpenses`, `from`, `to`, `sort`, `category` as implemented in
  `TransfersQueryService`. Filtering is done with the ORM.
- Bizum types and the `TRICOUNT` category are not ported.

Tests: transfer moves money and appears on both sides with the right sign;
insufficient funds 422; unknown destination 404; wrong PIN 422; currency
mismatch; each query param.

## Task 8: admin

Add to `iam`: `admin_views.py`, routes under `/admin/`, management command
`create_admin`.

- Four endpoints as in design section 2. Each view starts with an inline
  `if not request.user.is_admin` check returning 403 `FORBIDDEN`.
- Account and transfer listings reuse the banking and payments query services.
- Login and user responses gain `"admin": true|false`.

Tests: non-admin gets 403 on each route; admin can list, drill down, disable and
re-enable; disabling kills the target's existing tokens.

## Task 9: frontend

Copy the Vue app to `frontend/` (without `node_modules`, Docker, Cloud Build and
Terraform files), then:

1. Delete: `views/{TriccountView,GroupDetailView,SocialView,BizumView,PersonalView}.vue`
   if they only serve dropped features (check `PersonalView` and
   `DashboardView` first), `stores/tricount.js`, `components/modals/{AcceptRequestModal,AddContactModal,ViewContactModal,SendBizum}.vue`,
   and their tests.
2. Remove the matching routes, sidebar entries and `userService.js` functions.
3. Remove dashboard calls to `/users/{dni}/dashboard` and savings-goal calls.
4. Set the dev proxy target default to `http://localhost:8080`; remove the
   hard-coded Cloud Run URL from `apiClient.js`.
5. Add `views/AdminView.vue`, route `/admin` with `requiresAuth` and an admin
   check, sidebar link shown when `user.admin`, and admin functions in a new
   `api/adminService.js`.
6. Trim unit and Playwright tests to the remaining views; add a basic admin
   spec.

Check: `npm run build`, `npm run test:unit` (or the script name in
`package.json`), then a manual pass with both servers running: register, log
in, create account with a balance, transfer to a second user, see it in both
histories, add a card, edit profile, admin disables a user.

## Task 10: end-to-end check and inventory

1. Run the trimmed Playwright suite against Django.
2. Write `docs/vulnerability-inventory.md` as described in design section 11,
   using `docs/port-notes.md` and a read-through of the Django and Vue code.
3. Update the root `README.md`: what the project is, how to run both halves,
   pointer to the docs.
4. Hand over for team review. Tagging `baseline-vulnerable` and any planting
   decisions are the team's.

## Dependencies between tasks

1 → 2 → 3 → 4, 5 → 6, 7 → 8 → 9 → 10. Tasks 4 and 5 are independent of each
other once 3 is done; 6 and 7 both need 5.

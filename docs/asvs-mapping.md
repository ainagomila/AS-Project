# OWASP ASVS 5.0 mapping

State of `main` on 2026-11-01 (pull requests #1 to #13) against
[OWASP ASVS 5.0.0](https://github.com/OWASP/ASVS/tree/v5.0.0_release/5.0/en).
Requirement numbers are ASVS 5.0.0's own; the short text paraphrases the
requirement. The **Inventory** column points to
[`vulnerability-inventory.md`](vulnerability-inventory.md).

**Target.** Level 1 for the whole application, plus the Level 2 (and a few
Level 3) requirements that the six lab features address directly. This is a
self-assessment by the team, not a certified audit.

**Status.** *Met*, *Partly* (met with a stated gap), *Not met*.

**Feature to chapter:**

| Lab feature | Main ASVS requirements |
|---|---|
| Password protection in the database | V6.2, 11.4.2 |
| Server certificate | V12, 3.4.1 |
| OAuth 2.0 authentication | V6.3, V7, V10 |
| Database encryption | V11.1 to V11.3, V14 |
| Automated vulnerability checking | V15.1, V15.2 |
| Privacy rules (XACML) | V8, V16.3 |

**Not applicable:** V5 File Handling (no uploads), V9 Self-contained Tokens
(the API uses opaque reference tokens; only the OIDC ID token is a JWT, and the
backend issues it), V17 WebRTC, 4.3 GraphQL, 4.4 WebSocket, 6.5 to 6.7 (no
OTP, MFA devices or certificate login). Not assessed: 10.2 and 10.5 (the OAuth
client side, handled by the `oidc-client-ts` library).

## V1 Encoding and Sanitization

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 1.2.1 | Context-aware output encoding | Vue template escaping, no `v-html`; the login page is a Django template (autoescape) | Met | section 5 |
| 1.2.4 | Parameterised queries or ORM | Django ORM only, no raw SQL | Met | section 4 |
| 1.2.5 | No OS command injection | No OS calls in application code (Bandit, Semgrep) | Met | S1 |
| 1.3.2 | No `eval` or dynamic code execution | None in backend or frontend | Met | section 5 |
| 1.5.1 | XML parsers without external entities | The XACML policy loader rejects DTDs and entities; the policy is a local file | Met | X2 |

## V2 Validation and Business Logic

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 2.1.1 | Input validation rules documented | Rules are in `backend/common/validators.py` and the README test data, not in one document | Partly | |
| 2.2.1 | Input validated against business expectations | DNI control letter, Spanish IBAN, phone, email, amounts (positive, two decimals); PAN (Luhn) and CVV in the verifier. Some malformed input is still a 500 | Partly | B6, B9 |
| 2.2.2 | Validation enforced server-side | Every check is in the backend; frontend checks are for usability | Met | B11 |
| 2.3.2 | Business limits enforced (L2) | No transfer limit; every registration gets 100 EUR | Not met | B4, B6 |
| 2.3.3 | Business operations in transactions (L2) | Transfers in one `transaction.atomic()` | Met | B3 |
| 2.3.4 | Locking for limited resources (L2) | Both accounts locked with `select_for_update` | Met | B3 |
| 2.4.1 | Anti-automation (L2) | Lockout on wrong secrets; registration is unlimited | Partly | A5, B4 |

## V3 Web Frontend Security

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 3.2.2 | Text rendered with safe functions | Vue text interpolation | Met | |
| 3.3.1 | Cookies `Secure` and `__Host-`/`__Secure-` prefixed | Session and CSRF cookies are `Secure`, but keep Django's default names (`sessionid`, `csrftoken`) | Partly | T2 |
| 3.3.4 | Script-inaccessible cookies `HttpOnly` (L2) | Session and CSRF cookies `HttpOnly`; tokens are never in cookies | Met | T2 |
| 3.4.1 | HSTS of at least 1 year on all responses | Backend: 1 year, `includeSubDomains`, `preload` (with `DEBUG` off). The Vue pages from the Vite dev server have no HSTS | Partly | T2 |
| 3.4.2 | CORS origin from an allowlist | `CORS_ALLOWED_ORIGINS` (django-cors-headers) | Met | |
| 3.4.3, 3.4.4, 3.4.5, 3.4.6 | CSP, `nosniff`, Referrer-Policy, `frame-ancestors` (L2) | All set on every backend response; not on the Vite-served Vue pages | Partly | T2 |
| 3.5.1 | Cross-origin requests to sensitive functions rejected | The API authenticates with a bearer header only, so a cross-site request carries no credentials; the login form has Django CSRF protection | Met | section 5 |
| 3.5.3 | No sensitive actions on GET | State changes use POST, PATCH, PUT or DELETE | Met | |

## V4 API and Web Service

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 4.1.1 | Correct `Content-Type` with charset | DRF `application/json`; login page `text/html; charset=utf-8` | Met | |

## V6 Authentication

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 6.1.1 | Anti-brute-force controls documented | Inventory A5, `backend/common/lockout.py` | Met | A5 |
| 6.2.1 | Passwords of at least 8 characters | 8 to 128 characters | Met | |
| 6.2.2 | Users can change their password | Profile page (`PATCH /users/{dni}`) | Met | |
| 6.2.3 | Change requires current and new password | Requires the 6-digit PIN, not the current password | Not met | |
| 6.2.4 | Checked against the top 3000 passwords | Not done (Django's `CommonPasswordValidator` is not used) | Not met | |
| 6.2.5 | No composition rules | Requires upper case, lower case, digit and special character | Not met | |
| 6.2.6 | Password fields use `type=password` | Login page and Vue forms (with a show toggle) | Met | |
| 6.2.7 | Paste and password managers allowed | Not blocked | Met | |
| 6.2.8 | Password verified exactly as received | No trimming or case change at login | Met | |
| 6.2.9 | Passwords of 64+ characters allowed (L2) | Up to 128 | Met | |
| 6.2.12 | Checked against breached passwords (L2) | Not done | Not met | |
| 6.3.1 | Brute-force controls implemented | 5 failures per (DNI, IP) in 15 minutes lock login and PIN checks | Met | A5 |
| 6.3.2 | No default accounts | None; staff roles are given to registered users with `set_role` | Met | X5 |
| 6.3.3 | MFA (L2) | Login is password only; the PIN is asked again for sensitive actions but is also a knowledge factor | Not met | |
| 6.3.8 | No user enumeration (L3) | One answer for unknown DNI and wrong secret at login, registration and reset | Met | A6 |
| 6.4.1 | Generated initial secrets are random and expire | No secrets are generated: users choose them | Met | |
| 6.4.2 | No hints or secret questions | None | Met | |
| 6.4.3 | Secure password reset (L2) | DNI and PIN only, no second channel | Not met | A4 |

## V7 Session Management

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 7.2.1 | Tokens verified by a trusted backend | Each API request looks up the access token in the backend database | Met | A1 |
| 7.2.2 | Dynamically generated session tokens | OAuth access and refresh tokens | Met | A1 |
| 7.2.3 | Reference tokens from a CSPRNG, 128+ bits | oauthlib `SystemRandom`, 30 characters from 62 (about 178 bits); stored hashed | Met | A1 |
| 7.2.4 | New token on every authentication | Each login issues new tokens; Django rotates the login session | Met | A1 |
| 7.3.1 | Inactivity timeout (L2) | Tokens last 5 minutes; the app signs out unless the user extends | Met | A7 |
| 7.3.2 | Absolute session lifetime (L2) | None: extending renews indefinitely | Not met | A7 |
| 7.4.1 | Terminated sessions cannot be reused | Logout revokes access and refresh tokens server-side | Met | A7 |
| 7.4.2 | Sessions end when the account is disabled or deleted | Tokens revoked or deleted | Met | A2 |
| 7.4.3 | Other sessions ended after a credential change (L2) | Automatic on password change and reset | Met | A2 |
| 7.5.1 | Re-authentication before changing email, phone or credentials (L2) | The PIN is required, not a full re-authentication | Partly | |

## V8 Authorization

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 8.1.1 | Function- and data-level rules documented | The XACML policy is the rule set; roles in the README | Met | X2 |
| 8.2.1 | Function-level access only with explicit permission | PEP on every view, deny unless Permit; a test fails on an unenforced route | Met | X2 |
| 8.2.2 | Data-level access (IDOR, BOLA) | The policy compares the resource owner from the PIP; foreign objects answer 404 | Met | X3 |
| 8.2.3 | Field-level access (L2) | `mask-personal-data` obligation for staff; admins get no birthdate or gender | Met | X1, X5 |
| 8.3.1 | Enforced at a trusted service layer | Backend PEP and PDP; frontend guards are cosmetic | Met | B11 |

## V10 OAuth and OIDC

Kofre's backend is the authorization server, OpenID provider and resource
server; the Vue app is a public client.

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 10.1.1 | Tokens only where needed (L2) | Tokens are in browser memory (no backend-for-frontend) | Partly | A3 |
| 10.3.2 | Resource server enforces token scope and subject (L2) | The policy refuses tokens without the `banking` scope; the subject comes from the token | Met | X2 |
| 10.4.1 | Redirect URIs from an exact allowlist | One registered `https` callback; django-oauth-toolkit compares scheme, host, port and path and rejects fragments and user info | Met | A1 |
| 10.4.2 | Code usable once; reuse revokes issued tokens | The code is deleted on first use; tokens issued from it are not revoked on reuse | Partly | A1 |
| 10.4.3 | Short-lived code (10 minutes max) | 60 seconds | Met | A1 |
| 10.4.4 | Only needed grants; no implicit or password grant | `kofre-web` has the authorization-code grant only; implicit and password grants disabled | Met | A1 |
| 10.4.5 | Refresh token replay mitigated | Rotation, and reuse of an old refresh token revokes the session | Met | A1 |
| 10.4.6 | PKCE required, S256 (L2) | `PKCE_REQUIRED`, `plain` rejected | Met | A1 |
| 10.4.8 | Absolute refresh token expiry (L2) | Each refresh token lasts 5 minutes, but rotation has no overall end | Not met | A7 |
| 10.4.9 | Users can revoke tokens (L2) | Logout revokes; no list of active sessions | Partly | A7 |
| 10.6.1 | No implicit response types (L2) | `code` only | Met | A1 |
| 10.6.2 | Forced-logout DoS mitigated (L2) | `/o/logout/` validates `id_token_hint` and prompts without it | Met | A7 |
| 10.7.1 | User consents to each authorization (L2) | Skipped for the first-party client (`skip_authorization`) | Partly | |

## V11 Cryptography

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 11.1.1 | Key management policy (L2) | Keyring with key ids, rotation command, separate index key; no written lifecycle | Partly | E4 |
| 11.1.2 | Cryptographic inventory (L2) | Table below | Partly | |
| 11.2.1 | Industry-validated libraries (L2) | `cryptography`, `argon2-cffi`, Python `hmac` and `ssl` | Met | |
| 11.2.2 | Crypto agility (L2) | Versioned ciphertext `v1:<key id>:...`; Django hasher list | Met | E4 |
| 11.2.3 | At least 128-bit security (L2) | AES-256 and HMAC-SHA256 yes; the OIDC signing key and the mkcert certificate are RSA 2048 (about 112 bits) | Partly | |
| 11.3.1 | No ECB or weak padding | AES-GCM only | Met | |
| 11.3.2 | Approved ciphers and modes | AES-256-GCM | Met | E5 |
| 11.3.3 | Authenticated encryption (L2) | GCM, bound to table, column and row as associated data | Met | E5 |
| 11.4.1 | Approved hash functions | SHA-256 (HMAC, HKDF); no MD5 or SHA-1 | Met | |
| 11.4.2 | Passwords stored with a slow KDF (L2) | Argon2id, m=100 MiB, t=2, p=8, for password and PIN | Met | P1, P3 |
| 11.5.1 | CSPRNG with 128+ bits for secrets (L2) | Tokens (`SystemRandom`), GCM nonces (`os.urandom`), CSP nonces (`secrets`) | Met | |

Cryptographic inventory:

| Use | Algorithm | Key and where it lives |
|---|---|---|
| Passwords, user PIN | Argon2id | none (salted hash) |
| DNI, email, phone, PAN, card PIN | AES-256-GCM | keyring `backend/.env.d/encryptionKey64.json` or `SECURITY_ENCRYPTION_KEY_BASE64` |
| Blind indexes (DNI, phone, PAN) | HMAC-SHA256 | separate index key in the same keyring |
| OIDC ID token signature | RS256, RSA 2048 | `backend/.env.d/oidc.key` or `OIDC_RSA_PRIVATE_KEY` |
| Session and CSRF cookie signing | HMAC (Django) | `DJANGO_SECRET_KEY` in `.env` |
| CVV derivation in the verifier | HMAC-SHA256 | `VERIFIER_SECRET_KEY` in `.env` |
| HTTPS | TLS 1.2+, mkcert certificate (RSA 2048) | `backend/.certs/` |

## V12 Secure Communication

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 12.1.1 | TLS 1.2 or later only | Backend `minimum_version = TLSv1_2`; Node (Vite) defaults to 1.2 | Met | T1 |
| 12.1.2 | Recommended cipher suites (L2) | OpenSSL defaults, not tuned | Partly | T1 |
| 12.2.1 | TLS for all client connections, no fallback | Backend speaks HTTPS only; Vite serves HTTPS in Compose (it falls back to HTTP only when no certificate exists) | Met | T1 |
| 12.2.2 | Publicly trusted certificates | Local mkcert CA, trusted only on the developer's machine | Not met | T1 |
| 12.3.1, 12.3.3 | TLS between internal services and to the database (L2) | Backend to Postgres and backend to verifier are plain HTTP or TCP inside the Compose networks | Not met | T1 |
| 12.3.2 | TLS clients validate certificates (L2) | The Vite proxy verifies the backend against `rootCA.pem` | Met | T1 |

## V13 Configuration

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 13.2.1 | Backend components authenticate each other (L2) | Postgres needs a password; the verifier is unauthenticated, reachable only on an `internal` network | Partly | |
| 13.2.3 | No default service credentials (L2) | Database password generated per install | Met | D2 |
| 13.3.1 | Secrets in a secrets manager (L2) | Gitignored `.env` and `backend/.env.d` files | Not met | E4 |
| 13.4.1 | No source control metadata deployed | Images are built from the service folders; `.git` is never copied | Met | |
| 13.4.2 | Debug modes off (L2) | Django `DEBUG` off by default; the frontend and backend still run development servers | Partly | D1, D4 |
| 13.4.5 | No exposed documentation or monitoring endpoints (L2) | Swagger and actuator removed in the port | Met | section 4 |

## V14 Data Protection

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 14.1.1 | Sensitive data identified and classified (L2) | The inventory names what is hashed, encrypted or clear; no formal classification | Partly | E2 |
| 14.2.1 | No sensitive data in URLs | Tokens are refused in the query string, but customer URLs carry DNI, IBAN and PAN | Not met | B12 |
| 14.3.1 | Client data cleared when the session ends | Tokens and profile are only in memory | Met | A3 |
| 14.3.2 | Anti-caching headers (L2) | No `Cache-Control: no-store` on API responses | Not met | |
| 14.3.3 | No sensitive data in browser storage (L2) | Only the PKCE state in `sessionStorage` | Met | A3 |

## V15 Secure Coding and Architecture

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 15.1.1 | Remediation time frames for vulnerable components documented | CI blocks CRITICAL and HIGH findings on every pull request and suppressions expire; no time frame written for MEDIUM and LOW | Partly | S1 |
| 15.1.2 | Component inventory (SBOM) (L2) | Lockfiles (`uv.lock`, `package-lock.json`), no SBOM | Partly | S1 |
| 15.2.1 | No components past their remediation time frame | Last scan: no known vulnerable dependency (pip-audit, npm audit, Trivy) | Met | S1 |
| 15.3.1 | Only required fields returned | Responses built field by field; `verify-card` returns PAN and expiry only; staff views masked | Met | X1, X4 |
| 15.3.3 | Mass assignment prevented (L2) | Views read named fields only | Met | section 5 |

## V16 Security Logging and Error Handling

| ID | Requirement | Where met | Status | Inventory |
|---|---|---|---|---|
| 16.2.1 | Log entries say who, what, when, where (L2) | `AuditEvent`: time, subject id and role, action, resource, decision, rule, status, IP | Met | X5 |
| 16.3.1 | Authentication attempts logged (L2) | Logins and failed logins are not recorded | Not met | B13 |
| 16.3.2 | Failed authorization logged (L2) | Every denial is audited | Met | X5 |
| 16.3.3 | Security events and bypass attempts logged (L2) | Lockouts and wrong PINs are not logged on their own | Partly | B13 |
| 16.4.2 | Logs protected from modification (L2) | Append-only through the ORM; a database user can still change rows | Partly | X5 |
| 16.5.1 | Generic message on unexpected errors (L2) | Unhandled errors return the exception text | Not met | B8 |
| 16.5.2 | Secure when an external resource fails (L2) | Verifier down: the card is refused with `INFRA_ERROR` | Met | E1 |
| 16.5.3 | No fail-open (L2) | The PEP denies NotApplicable, Indeterminate and unknown obligations; transfers roll back | Met | X2, B3 |

## Level 1 gaps

Level 1 requirements not met, or only partly: 2.1.1, 2.2.1 (B9), 3.3.1 (cookie
prefix), 3.4.1 (no HSTS on the Vite pages), 6.2.3, 6.2.4, 6.2.5 (password
policy), 10.4.2 (code reuse does not revoke tokens), 12.2.2 (local CA),
14.2.1 (B12), 15.1.1. The quickest to close are 6.2.4 and 6.2.5 (Django's
password validators instead of the composition rules) and 3.3.1
(`SESSION_COOKIE_NAME`, `CSRF_COOKIE_NAME` with a `__Host-` prefix).

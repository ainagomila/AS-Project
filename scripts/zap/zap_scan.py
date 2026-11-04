#!/usr/bin/env python3
"""Kofre + OWASP ZAP: seed every API feature through ZAP, verify each step, then run an
authenticated active scan and write an HTML report.

Roles covered: customer, admin, auditor, operations. Everything created during the run is deleted at the end (KEEP_DATA=1 keeps it).
Every call has an expected status. If any step is unexpected the script stops BEFORE scanning
(set ALLOW_FAILURES=1 to scan anyway). Needs: pip install requests. Local test environments only.
"""
import base64, hashlib, hmac, html, json, os, re, secrets, shlex, shutil, subprocess, sys, time
from collections import Counter, deque
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
import urllib3

urllib3.disable_warnings()

ROOT = Path(__file__).resolve().parents[2]
BASE = os.getenv("KOFRE_BASE", "https://localhost:8080")
FRONT = os.getenv("KOFRE_FRONT", "https://localhost:5173")
ZAP = os.getenv("ZAP_URL", "http://127.0.0.1:8090")
ZAP_KEY = os.getenv("ZAP_API_KEY", "changeme")
DNI = os.getenv("KOFRE_DNI", "11111111H")
PASSWORD = os.getenv("KOFRE_PASSWORD", "Secret_123")
PASSWORD2 = "Other_456"
PIN = os.getenv("KOFRE_PIN", "123456")
NEWPIN = "654321"
EMAIL2, PHONE2 = "zap.test2@example.com", "+34600111222"
IBAN = os.getenv("KOFRE_IBAN", "ES9121000418450200051332")
IBAN2 = "ES6800491500042110123456"  # throw-away account, deleted at the end
PAN = os.getenv("KOFRE_PAN", "4111111111111111")
EXP = os.getenv("KOFRE_EXP", "12/28")
PAN2, EXP2 = "5555555555554444", "11/29"  # throw-away card, deleted at the end
CARD_PIN = os.getenv("KOFRE_CARD_PIN", "1234")
# Staff roles cannot be created through the API: the script registers these users and each one
# is promoted once with `manage.py set_role`. role -> (DNI, phone)
STAFF = {
    "admin": (os.getenv("KOFRE_ADMIN_DNI", "44444444A"), "+34600444444"),
    "auditor": (os.getenv("KOFRE_AUDITOR_DNI", "55555555K"), "+34600555555"),
    "operations": (os.getenv("KOFRE_OPERATIONS_DNI", "66666666Q"), "+34600666666"),
}
MANAGE = os.getenv("KOFRE_MANAGE_CMD", "docker compose exec -T backend uv run python manage.py")
TEMP2_DNI, TEMP2_PHONE = "88888888Y", "+34600888888"  # customer deleted through /admin during the seed
TEMP_DNI, TEMP_PHONE = "77777777B", "+34600777777"  # customer created and deleted through /admin
DISPOSABLE_DNI = "22222222J"  # customer whose PATCH/DELETE /users/{dni} and reset-password get attacked
# customers the script can re-create when the scan destroys them: dni -> (name, phone, email, birthdate, gender)
SCAN_USERS = {DNI: ("ZAP Test", "+34600123456", "zap.test@example.com", "1990-01-01", "MALE"),
              DISPOSABLE_DNI: ("ZAP Disposable", "+34600222222", "zap.disposable@example.com", "1988-08-08", "OTHER")}
STALE_DNIS = [TEMP_DNI, TEMP2_DNI, DISPOSABLE_DNI] + [dni for dni, _ in STAFF.values()]  # recreated on every run
RESTART = os.getenv("KOFRE_RESTART_CMD", "docker compose restart backend")  # "" disables it
WARN_SHARE = 0.10  # warn when more than this share of the scan's responses are 401 or 429
SCAN_AS = os.getenv("SCAN_AS", "all")  # all | customer | admin | auditor | operations
SCAN_MODE = os.getenv("SCAN_MODE", "routes")  # routes: one active scan per route | tree: one recursive scan
ALLOW_FAILURES = os.getenv("ALLOW_FAILURES") == "1"
REPORT = Path(os.getenv("ZAP_REPORT", ROOT / "security-reports" / "zap-report.html"))
CLIENT = "kofre-web"
REDIRECT = f"{FRONT.rstrip('/')}/callback"
SCAN_DNI = {"customer": DNI, "disposable": DISPOSABLE_DNI, **{role: dni for role, (dni, _) in STAFF.items()}}

s = requests.Session()  # app traffic goes through ZAP so it learns every URL
s.verify = False
s.trust_env = False
s.proxies = {"http": ZAP, "https": ZAP}
z = requests.Session()  # ZAP API, direct
z.trust_env = False

COVER, STATS, AUTHZ = {}, {}, []  # per-role scan table, per-role response stats, authorization checks
RESULTS = []  # (label, status, ok, expected)
SKIPPED = []


TTY = sys.stdout.isatty()


def _width():
    return shutil.get_terminal_size((100, 20)).columns - 1


def clear_line():
    if TTY:
        sys.stdout.write("\r" + " " * _width() + "\r")


def status_line(text):
    """Rewrite a single console line in place (cut to the window width so it never wraps)."""
    if TTY:
        sys.stdout.write("\r" + text[:_width()].ljust(_width()))
        sys.stdout.flush()


def log(*parts):
    """print() that first wipes the status line, so permanent messages stay readable."""
    clear_line()
    print(*parts, flush=True)


def vlog(*parts):
    """Detail lines: shown only with ZAP_VERBOSE=1 (the verdict has the summary)."""
    if os.getenv("ZAP_VERBOSE") == "1":
        log(*parts)


def record(label, status, expect, body=""):
    """Store a step result; OK steps only refresh the status line, FAILs become real lines."""
    ok = status in expect
    RESULTS.append((label, status, ok, expect))
    if ok:
        status_line(f"seed step {len(RESULTS)}: {label} -> {status}")
    else:
        log(f"FAIL {label} -> {status} (expected {expect}) {body[:150]}")
    return ok


def bar(pct, width=20):
    filled = pct * width // 100
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def latest_request():
    """Method and path of the last request ZAP recorded, i.e. what is being attacked right now."""
    try:
        n = message_count()
        message = zap("core/view/messages", baseurl=BASE, start=max(n - 1, 0), count=1)["messages"][0]
        method, url = message["requestHeader"].split(" ", 2)[:2]
        return f"{method} {url.replace(BASE, '')}"
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return ""


def zap(path, timeout=60, **params):
    r = z.get(f"{ZAP}/JSON/{path}/", params={"apikey": ZAP_KEY, **params}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def scan_states():
    return [(x["id"], x["state"]) for x in zap("ascan/view/scans")["scans"]]


def verifier_key():
    key = os.getenv("VERIFIER_SECRET_KEY")
    if key:
        return key
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("VERIFIER_SECRET_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("VERIFIER_SECRET_KEY not found in .env")


def cvv(pan, exp):
    tag = hmac.new(verifier_key().encode(), f"{pan}E{exp}".encode(), hashlib.sha256).digest()
    return "%03d" % (int.from_bytes(tag, "big") % 1000)


def card_body(pan, exp, alias):
    return {"pan": pan, "expireDate": exp, "alias": alias, "cvv": cvv(pan, exp),
            "pin": CARD_PIN, "type": "DEBIT", "bank": "Kofre"}


def user_payload(name, dni, phone, email, birthdate="1985-05-05", gender="OTHER"):
    """Body shared by /auth/register and POST /admin/users."""
    return {"name": name, "dni": dni, "email": email, "phone": phone, "password": PASSWORD,
            "birthdate": birthdate, "gender": gender, "pin": PIN}


def follow(r):
    """Follow redirects by hand; stop at the OAuth callback and return its URL."""
    for _ in range(8):
        if not r.is_redirect:
            return r, None
        loc = urljoin(r.url, r.headers["Location"])
        if loc.startswith(REDIRECT):
            return r, loc
        r = s.get(loc, allow_redirects=False)
    raise RuntimeError("too many redirects")


def login(dni=None, password=None):
    dni, password = dni or DNI, password or PASSWORD
    s.cookies.clear()  # otherwise a previous user's session skips the login form
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    r, loc = follow(s.get(f"{BASE}/o/authorize/", allow_redirects=False, params={
        "response_type": "code", "client_id": CLIENT, "redirect_uri": REDIRECT,
        "scope": "openid banking", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"}))
    if loc is None:  # login page
        csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
        nxt = re.search(r'name="next" value="([^"]*)"', r.text)
        if not csrf:
            raise RuntimeError(f"login page not found ({r.status_code})")
        r, loc = follow(s.post(r.url, allow_redirects=False, headers={"Referer": r.url}, data={
            "username": dni, "password": password, "csrfmiddlewaretoken": csrf.group(1),
            "next": html.unescape(nxt.group(1)) if nxt else ""}))
    if loc is None:
        raise RuntimeError(f"login failed for {dni} ({r.status_code}): wrong credentials, or "
                           "locked out (429: wait 15 min or restart the backend)")
    q = parse_qs(urlparse(loc).query)
    if q.get("state", [None])[0] != state:
        raise RuntimeError("OAuth state mismatch")
    t = s.post(f"{BASE}/o/token/", data={
        "grant_type": "authorization_code", "code": q["code"][0], "redirect_uri": REDIRECT,
        "client_id": CLIENT, "code_verifier": verifier})
    t.raise_for_status()
    status_line(f"login OK ({dni})")
    return t.json()


def refresh(tok, dni=None):
    # direct, not through ZAP: a recorded refresh_token request would be replayed by the scan
    t = z.post(f"{BASE}/o/token/", verify=False, timeout=30, data={
        "grant_type": "refresh_token", "refresh_token": tok["refresh_token"], "client_id": CLIENT})
    if t.status_code != 200:
        try:
            return login(dni)
        except RuntimeError as e:
            dni = dni or DNI
            if dni not in SCAN_USERS:
                raise
            # the active scan changed or deleted this user (PATCH/DELETE /users/{dni}): recreate it
            log(f"[!] {time.strftime('%H:%M:%S')} {dni} lost during the scan ({e}), re-registering it")
            # pause ZAP meanwhile: its running scan keeps sending reset-password for this DNI (valid pin)
            # and would overwrite the new password before login()
            zap("ascan/action/pauseAllScans")
            log(f"    {time.strftime('%H:%M:%S')} after pause: {scan_states()}")
            try:
                delete_users_by_dni([dni])
                register_scan_user(dni)
                return login(dni)
            finally:
                zap("ascan/action/resumeAllScans")
                log(f"    {time.strftime('%H:%M:%S')} recovery finished, ZAP scans resumed: {scan_states()}")
                time.sleep(2)
                log(f"    {time.strftime('%H:%M:%S')} +2 s: {scan_states()}")
    return {**tok, **t.json()}


def logout(tok):
    r = s.get(f"{BASE}/o/logout/", allow_redirects=False, params={
        "id_token_hint": tok["id_token"], "client_id": CLIENT,
        "post_logout_redirect_uri": FRONT.rstrip("/") + "/"})
    record("GET /o/logout/", r.status_code, (200, 302))
    s.cookies.clear()


def call(method, path, tok=None, expect=(200, 201, 204), **kw):
    headers = {"Authorization": f"Bearer {tok['access_token']}"} if tok else {}
    r = s.request(method, BASE + path, headers=headers, **kw)
    record(f"{method} {path}", r.status_code, expect, r.text)
    return r


def jget(r, default):
    try:
        return r.json()
    except ValueError:
        return default


def clear_bearer():
    try:
        zap("replacer/action/removeRule", description="kofre-bearer")
    except requests.RequestException:  # no such rule, or ZAP unreachable
        pass


def reset_zap():
    """Start from a clean ZAP: no scan left running, no old history or alerts, no stale token rule."""
    try:
        zap("core/view/version")
    except requests.RequestException as e:
        sys.exit(f"ZAP is not reachable at {ZAP} ({type(e).__name__}). Start the ZAP daemon first; "
                 "from WSL, run the script in PowerShell instead (or set ZAP_URL to the Windows host).")
    zap("ascan/action/stopAllScans")
    try:
        zap("core/action/newSession", timeout=300, overwrite="true")
    except requests.ReadTimeout:
        sys.exit("ZAP did not open a new session within 5 min (it is probably out of memory after the "
                 "last scan). Restart the ZAP daemon and run the script again.")
    clear_bearer()


def set_bearer(token):
    clear_bearer()
    zap("replacer/action/addRule", description="kofre-bearer", enabled="true", matchType="REQ_HEADER",
        matchRegex="false", matchString="Authorization", replacement=f"Bearer {token}", initiators="")


def seed_customer():
    # 1. remove the previous test user through the API (422: an earlier scan changed its PIN)
    try:
        tok = login()
        call("DELETE", f"/users/{DNI}", tok, expect=(204, 422), json={"pin": PIN})
    except Exception as e:
        log(f"[i] no previous user / cannot log in: {e}")
    delete_users_by_dni([DNI])  # fallback when the API delete was not possible
    # 2. register, login, logout, login
    call("POST", "/auth/register", expect=(201,), json=user_payload(
        "ZAP Test", DNI, "+34600123456", "zap.test@example.com", "1990-01-01", "MALE"))
    tok = login()
    logout(tok)
    tok = login()
    d = f"/users/{DNI}"
    # 3. profile and security
    call("GET", d, tok)
    call("GET", "/users", tok, expect=(200, 403))
    call("POST", f"{d}/security/verify-pin", tok, json={"pin": PIN})
    call("POST", f"{d}/security/verify-password", tok, json={"pin": PIN})
    call("PATCH", d, tok, json={"pin": PIN, "email": EMAIL2})
    call("PATCH", d, tok, json={"pin": PIN, "phone": PHONE2})
    call("PATCH", d, tok, json={"pin": PIN, "password": PASSWORD2})
    call("PATCH", d, tok, json={"pin": PIN, "password": PASSWORD})
    call("PATCH", d, tok, json={"pin": PIN, "newPin": NEWPIN})
    call("PATCH", d, tok, json={"pin": NEWPIN, "newPin": PIN})
    # 4. accounts and cards
    for iban, name in ((IBAN, "ZAP account"), (IBAN2, "ZAP temp")):
        call("POST", f"{d}/accounts", tok, expect=(201,), json={
            "iban": iban, "name": name, "bank": "Kofre", "currency": "EUR"})
    call("PATCH", f"{d}/accounts/{IBAN}", tok, json={"name": "ZAP account renamed"})
    call("POST", f"{d}/accounts/{IBAN}/cards", tok, expect=(201,), json=card_body(PAN, EXP, "zap"))
    call("POST", f"{d}/accounts/{IBAN2}/cards", tok, expect=(201,), json=card_body(PAN2, EXP2, "temp"))
    cd = f"{d}/accounts/{IBAN}/cards/{PAN}"
    call("PATCH", cd, tok, json={"alias": "zap renamed"})
    call("PATCH", cd, tok, json={"status": "FREEZED"})
    call("PATCH", cd, tok, json={"status": "ACTIVE"})
    call("GET", cd, tok)
    call("POST", f"{cd}/security/verify-card", tok, json={"pin": PIN})
    # 5. transfers: from the auto-created "Kofre" account (100 EUR) to ours
    accs = jget(call("GET", f"{d}/accounts", tok), {}).get("accounts", [])
    src = next((a["iban"] for a in accs if a.get("iban") and a["iban"] not in (IBAN, IBAN2)), None)
    if src:
        call("POST", f"{d}/accounts/{src}/transfers", tok, expect=(200,), json={
            "beneficiary": "ZAP Test", "destinationIban": IBAN, "amount": 5.00, "currency": "EUR",
            "concept": "zap seed", "pin": PIN, "categories": ["FOOD", "OTHER"]})
        call("GET", f"{d}/accounts/{src}/transfers", tok)
        call("GET", f"{d}/accounts/{src}/transfers", tok, params={"q": "zap", "onlyExpenses": "true"})
    else:
        RESULTS.append(("find the auto-created source account", 0, False, ("an IBAN",)))
        log("FAIL no source account found for the transfer")
    call("GET", f"{d}/accounts/{IBAN}/transfers", tok)
    # 6. read endpoints
    for p in (f"{d}/cards", f"{d}/accounts/{IBAN}", f"{d}/accounts/{IBAN}/cards"):
        call("GET", p, tok)
    # 7. delete the throw-away card and account
    call("DELETE", f"{d}/accounts/{IBAN2}/cards/{PAN2}", tok, expect=(204,), json={"pin": PIN})
    call("DELETE", f"{d}/accounts/{IBAN2}", tok, expect=(204,), json={"pin": PIN})
    # 8. public reset-password (revokes ALL the user's tokens, so it goes last, then log in again)
    call("POST", "/auth/reset-password", expect=(204,), json={"dni": DNI, "pin": PIN, "newPassword": PASSWORD})
    return login()


SNAPSHOT_CODE = """
import json
from banking.models import Account, Card
from iam.models import User
from payments.models import Payment
print("SNAPSHOT" + json.dumps({
    "users": list(User.objects.values_list("id", flat=True)),
    "accounts": list(Account.objects.values_list("id", flat=True)),
    "cards": list(Card.objects.values_list("id", flat=True)),
    "payments": list(Payment.objects.values_list("id", flat=True)),
}))
"""

PURGE_CODE = """
import json
from banking.models import Account, Card
from iam.models import User
from payments.models import Payment
snap = json.loads(r'''__SNAPSHOT__''')
purged = {}
for key, model in (("payments", Payment), ("cards", Card), ("accounts", Account), ("users", User)):
    purged[key] = model.objects.exclude(id__in=snap[key]).delete()[0]
print("PURGED" + json.dumps(purged))
"""


def run_backend(args, stdin=None):
    """Run `manage.py <args>` inside the backend container and return its stdout."""
    cmd = shlex.split(MANAGE) + shlex.split(args)
    return subprocess.run(cmd, cwd=ROOT, input=stdin, check=True, capture_output=True,
                          text=True, timeout=180).stdout


def backend_error(e):
    return getattr(e, "stderr", None) or e


def snapshot_data():
    """IDs that exist before the run, so everything created afterwards can be purged."""
    try:
        out = run_backend("shell", SNAPSHOT_CODE)
        return out[out.index("SNAPSHOT") + len("SNAPSHOT"):].strip()
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        log(f"[!] cannot snapshot the database, cleanup disabled: {backend_error(e)}")
        return None


def purge_new_data(snapshot):
    """Delete users, accounts, cards and payments created since the snapshot (ZAP's included).

    The append-only audit log is kept on purpose. KEEP_DATA=1 skips the purge.
    """
    if snapshot is None or os.getenv("KEEP_DATA") == "1":
        return
    try:
        out = run_backend("shell", PURGE_CODE.replace("__SNAPSHOT__", snapshot))
        log("cleanup:", out[out.index("PURGED") + len("PURGED"):].strip())
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        log(f"[!] cleanup failed, remove the test data by hand: {backend_error(e)}")


DELETE_USERS_CODE = """
import json
from banking.models import Account, Card
from iam.services import find_by_dni
for dni in json.loads(r'''__DNIS__'''):
    user = find_by_dni(dni)
    if user is None:
        continue
    ids = list(Account.objects.filter(user_id=user.id).values_list("id", flat=True))
    Card.objects.filter(account_id__in=ids).delete()
    Account.objects.filter(id__in=ids).delete()
    user.delete()
"""


def delete_users_by_dni(dnis):
    """Remove leftover test users (and their accounts and cards) straight from the database."""
    try:
        run_backend("shell", DELETE_USERS_CODE.replace("__DNIS__", json.dumps(dnis)))
    except (OSError, subprocess.SubprocessError) as e:
        log(f"[!] could not remove stale users {dnis}: {backend_error(e)}")


def restart_backend():
    """A restart clears the in-memory lockout counters left by earlier runs and by ZAP."""
    if not RESTART:
        return
    try:
        subprocess.run(shlex.split(RESTART), cwd=ROOT, check=True, capture_output=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as e:
        log(f"[!] backend restart failed, a previous lockout may still apply: {backend_error(e)}")
        return
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            z.get(f"{BASE}/o/.well-known/openid-configuration", verify=False, timeout=3)
            return  # any HTTP answer means the server is up
        except requests.RequestException:
            time.sleep(2)
    sys.exit("the backend did not come back within 90 s after the restart")


def ensure_role(role, dni):
    """Roles cannot be set through the API; set_role is idempotent, so run it on every pass."""
    try:
        run_backend(f"set_role {dni} {role}")
        status_line(f"role {role} set for {dni}")
    except (OSError, subprocess.SubprocessError) as e:
        log(f"[!] could not set the {role} role automatically: {backend_error(e)}")


TOKENS_CODE = """
from iam.services import find_by_dni
from oauth2_provider.models import AccessToken, RefreshToken
user = find_by_dni("__DNI__")
print("TOKENS user_found=%s" % (user is not None))
if user:
    for t in AccessToken.objects.filter(user=user).order_by("created"):
        print("TOKENS AT created=%s expires=%s" % (t.created.strftime("%H:%M:%S"), t.expires.strftime("%H:%M:%S")))
    for t in RefreshToken.objects.filter(user=user).order_by("created"):
        print("TOKENS RT created=%s revoked=%s family=%s" % (
            t.created.strftime("%H:%M:%S"), t.revoked and t.revoked.strftime("%H:%M:%S"), str(t.token_family)[:8]))
"""


def token_state(dni):
    """Print the user's token rows (UTC) so revocations can be matched to the 401s above."""
    try:
        out = run_backend("shell", TOKENS_CODE.replace("__DNI__", dni))
        log(f"  token rows for {dni} (UTC):")
        for row in out.splitlines():
            if row.startswith("TOKENS"):
                log("    " + row[7:])
    except (OSError, subprocess.SubprocessError) as e:
        log(f"[!] cannot read token rows: {backend_error(e)}")


def has_role(role, r):
    """False (and a SKIPPED note) when the staff user was refused for lack of the role."""
    if r.status_code != 403:
        return True
    SKIPPED.append(f"{role}: no role yet. Run once, then re-run: "
                   + f"{MANAGE} set_role {STAFF[role][0]} {role}")
    return False


def needs_customer_id(role, uid):
    if uid is None:
        SKIPPED.append(f"{role}: needs the admin step first (it provides the customer id)")
    return uid is not None


def seed_admin(tok):
    """Exercise /admin/users. Returns the customer's id, which the other roles need."""
    r = call("GET", "/admin/users", tok, expect=(200, 403))
    if not has_role("admin", r):
        return None
    users = jget(r, [])
    uid = next((u["id"] for u in users if u.get("dni") == DNI), None)
    stale = next((u["id"] for u in users if u.get("dni") == TEMP_DNI), None)
    if stale:  # left over from an interrupted run
        call("DELETE", f"/admin/users/{stale}", tok, expect=(204,))
    if uid:
        call("PATCH", f"/admin/users/{uid}", tok, json={"active": True})
        call("GET", f"/admin/users/{uid}/accounts", tok, expect=(200, 403))
    # throw-away customer: the destructive operations run on it, never on the real one
    created = call("POST", "/admin/users", tok, expect=(201,), json=user_payload(
        "ZAP Temp", TEMP_DNI, TEMP_PHONE, "zap.temp@example.com"))
    temp = jget(created, {}).get("id")
    if temp:
        call("PATCH", f"/admin/users/{temp}", tok, json={"active": False})
        call("PATCH", f"/admin/users/{temp}", tok, json={"active": True})
        call("POST", f"/admin/users/{temp}", tok, json={"newPassword": PASSWORD2})
        # it stays alive: the scan attacks PATCH and POST /admin/users/{id} on it (a deleted id only gives 404)
    created2 = call("POST", "/admin/users", tok, expect=(201,), json=user_payload(
        "ZAP Temp2", TEMP2_DNI, TEMP2_PHONE, "zap.temp2@example.com"))
    temp2 = jget(created2, {}).get("id")
    if temp2:
        call("DELETE", f"/admin/users/{temp2}", tok, expect=(204,))
    return uid


def seed_auditor(tok, uid):
    if not needs_customer_id("auditor", uid):
        return
    r = call("GET", f"/admin/users/{uid}/accounts", tok, expect=(200, 403))
    if not has_role("auditor", r):
        return
    accounts = jget(r, {}).get("accounts", [])
    if accounts:
        call("GET", f"/admin/users/{uid}/accounts/{accounts[0]['id']}/transfers", tok)
    call("GET", "/admin/audit", tok)


def seed_operations(tok, uid):
    if not needs_customer_id("operations", uid):
        return
    r = call("GET", "/operations/accounts", tok, expect=(200, 403))
    if not has_role("operations", r):
        return
    cards = jget(call("GET", "/operations/cards", tok), {}).get("cards", [])
    owned = lambda items: next((i for i in items if i.get("ownerId") == uid), None)  # noqa: E731
    targets = (
        ("accounts", owned(jget(r, {}).get("accounts", [])), ("FROZEN", "ACTIVE")),
        ("cards", owned(cards), ("FREEZED", "ACTIVE")),
    )
    for kind, item, statuses in targets:  # freeze, then restore
        if item is None:
            RESULTS.append((f"find the customer's {kind} in /operations", 0, False, ("an item",)))
            continue
        for status in statuses:
            call("PATCH", f"/operations/{kind}/{item['id']}", tok,
                 json={"status": status, "reason": "zap seed"})


def seed_staff():
    tokens = {}
    for role, (dni, phone) in STAFF.items():
        call("POST", "/auth/register", expect=(201,), json=user_payload(
            f"ZAP {role}", dni, phone, f"zap.{role}@example.com"))
        ensure_role(role, dni)
        try:
            tokens[role] = login(dni)
        except Exception as e:
            RESULTS.append((f"login {role}", 0, False, ("login",)))
            log(f"FAIL {e}")
    uid = seed_admin(tokens["admin"]) if "admin" in tokens else None
    if "auditor" in tokens:
        seed_auditor(tokens["auditor"], uid)
    if "operations" in tokens:
        seed_operations(tokens["operations"], uid)
    return tokens


def register_scan_user(dni):
    name, phone, email, birthdate, gender = SCAN_USERS[dni]
    return call("POST", "/auth/register", expect=(201,),
                json=user_payload(name, dni, phone, email, birthdate, gender))


def seed_disposable():
    """Throw-away customer for the routes that destroy a user. Each request is recorded once here;
    the user is then re-created, so the scan finds it again (and re-creates it whenever it dies)."""
    d = f"/users/{DISPOSABLE_DNI}"
    register_scan_user(DISPOSABLE_DNI)
    tok = login(DISPOSABLE_DNI)
    call("GET", d, tok)
    call("PATCH", d, tok, json={"pin": PIN, "email": "zap.disposable.new@example.com"})
    call("POST", "/auth/reset-password", expect=(204,),
         json={"dni": DISPOSABLE_DNI, "pin": PIN, "newPassword": PASSWORD})
    tok = login(DISPOSABLE_DNI)  # reset-password revoked every token
    call("DELETE", d, tok, expect=(204,), json={"pin": PIN})
    register_scan_user(DISPOSABLE_DNI)
    return login(DISPOSABLE_DNI)


def authz_check(tokens):
    """Who must NOT reach what, checked directly (not through ZAP): ZAP's active scan does not try other
    users' ids in the path, so this is the evidence for cross-user and cross-role isolation."""
    for role in tokens:  # keep the stored refresh token valid: the scan refreshes it again later
        tokens[role] = refresh(tokens[role], SCAN_DNI[role])
    a, b = DNI, DISPOSABLE_DNI
    cases = [(None, "GET", f"/users/{a}", (401,)), (None, "GET", "/admin/users", (401,)),
             (None, "GET", "/operations/accounts", (401,)),
             ("customer", "GET", f"/users/{b}", (403, 404)), ("customer", "GET", f"/users/{b}/accounts", (403, 404)),
             ("disposable", "GET", f"/users/{a}", (403, 404)), ("disposable", "GET", f"/users/{a}/accounts", (403, 404)),
             ("disposable", "GET", f"/users/{a}/cards", (403, 404)),
             ("disposable", "GET", f"/users/{a}/accounts/{IBAN}/cards", (403, 404)),
             ("customer", "GET", "/admin/users", (403,)), ("customer", "GET", "/operations/accounts", (403,)),
             ("customer", "GET", "/admin/audit", (403,))]
    cases += [(role, "GET", f"/users/{a}/accounts", (403, 404)) for role in STAFF]
    for role, method, path, expect in cases:
        if role and role not in tokens:
            continue
        headers = {"Authorization": f"Bearer {tokens[role]['access_token']}"} if role else {}
        status = z.request(method, BASE + path, headers=headers, verify=False, timeout=15).status_code
        AUTHZ.append((role or "anonymous", method, path, status, expect))


def seed():
    tokens = {"customer": seed_customer()}
    tokens.update(seed_staff())
    tokens["disposable"] = seed_disposable()
    return tokens


def summary():
    bad = [x for x in RESULTS if not x[2]]
    log(f"\nseed: {len(RESULTS) - len(bad)}/{len(RESULTS)} steps as expected")
    for label, code, _, exp in bad:
        log(f"  FAIL {label} -> {code} (expected {exp})")
    for note in SKIPPED:
        log(f"  SKIPPED {note}")
    return not bad


def exclude_param(name):
    """Stop ZAP fuzzing `name`. Every wrong PIN it invents counts towards the lockout, which then
    answers 429 for the whole DNI and hides every other endpoint behind it."""
    try:
        rows = next(iter(zap("ascan/view/excludedParams").values()), [])
        if not any(isinstance(r, dict) and r.get("name") == name for r in rows):
            zap("ascan/action/addExcludedParam", name=name)
    except (requests.RequestException, ValueError) as e:
        log(f"[!] could not exclude the '{name}' parameter, expect 429s from the lockout: {e}")


# Each staff role only attacks its own subtree: the site tree is full of the customer's URLs, which
# a staff token can only answer 403, so scanning everything per role tests almost nothing.
SCOPE = {"admin": "/admin", "operations": "/operations", "auditor": "/admin"}


# Routes never attacked: they end the session or the scan user. (method or "*", route regex, why)
SKIP_ROUTES = (
    ("*", r"^/o/(logout|revoke_token)$", "ends the session"),
    ("*", r"^/auth/reset-password$", "revokes every token; covered by the disposable-user pass"),
    ("PATCH", r"^/users/\{dni\}$", "changes the scan user's credentials; covered by the disposable-user pass"),
    ("DELETE", r"^/users/\{dni\}$", "deletes the scan user; covered by the disposable-user pass"),
)


AUTH_FLOW = {"GET /o/authorize", "GET /accounts/login", "POST /accounts/login", "POST /o/token"}


def injectable(method, url, body):
    """False when ZAP has nothing to inject: no query string and no body field other than `pin`
    (excluded from fuzzing, see exclude_param). Such routes only get path-variant probes."""
    if urlparse(url).query:
        return True
    if not body:
        return False
    try:
        data = json.loads(body)
    except ValueError:
        return True  # form data
    return not isinstance(data, dict) or bool(set(data) - {"pin"})


def scan_targets(role, upto):
    """One (method, url, body, ok) per app route of `role`, taken from the seed traffic in ZAP's
    history: the last 2xx request of the route, else the last one."""
    best = {}
    app = {route_key(*label.split(" ", 1)) for label, *_ in RESULTS if " " in label} | AUTH_FLOW
    for start in range(0, upto, 500):
        for m in zap("core/view/messages", baseurl=BASE, start=start, count=min(500, upto - start))["messages"]:
            method, url = (m["requestHeader"].split(" ", 2) + ["", ""])[:2]
            parts = m["responseHeader"].split(" ", 2)
            ok = len(parts) > 1 and parts[1].startswith("2")
            key = route_key(method, urlparse(url).path)
            if urlparse(url).path.startswith("/users/") and SCAN_DNI.get(role) not in url:
                continue  # another user's resource: this role's token would only get 403/404
            score = (ok, injectable(method, url, m["requestBody"]))  # prefer 2xx, then a request with input
            if key in app and in_scope(role, key) and (key not in best or score >= best[key][3]):
                best[key] = (method, url, m["requestBody"], score)
    return best


def start_route_scans(role, only=None):
    """Start one active scan per route (exact method, URL and body from the seed), so each route is
    attacked on its own and the exclusions are per route and method, not per subtree.
    Returns ({route: scan id}, [(route, why it was not scanned)], {route: has injectable input})."""
    ids, notes, meta = {}, [], {}
    for key, (method, url, body, score) in sorted(scan_targets(role, SEED_END).items()):
        if only and key != only:
            continue
        why = next((w for m_, rx, w in SKIP_ROUTES
                    if m_ in ("*", method) and re.search(rx, key.split(" ", 1)[1])), None)
        if why and role != "disposable":
            notes.append((key, f"skipped by design: {why}"))
            continue
        meta[key] = score[1]
        try:
            ids[key] = zap("ascan/action/scan", url=url, method=method, recurse="false", inScopeOnly="false",
                           **({"postData": body} if body else {}))["scan"]
        except (requests.RequestException, KeyError, ValueError) as e:
            detail = getattr(getattr(e, "response", None), "text", "") or e
            notes.append((key, f"NOT STARTED: {str(detail)[:80]}"))
    return ids, notes, meta


def token_alive(tok):
    try:
        return z.get(f"{BASE}/o/userinfo/", headers={"Authorization": f"Bearer {tok['access_token']}"},
                     verify=False, timeout=10).status_code != 401
    except requests.RequestException:
        return True


def scan(tok, role, only=None):
    dni = SCAN_DNI[role]
    set_bearer(tok["access_token"])
    zap("ascan/action/excludeFromScan", regex=r".*/o/(logout|revoke_token)/.*")
    # ZAP's own fuzzing kills the session: DELETE/PATCH /users/{dni} removes or re-passwords the
    # test user and reset-password revokes every token, so the rest of the scan only sees 401/404.
    if SCAN_MODE == "tree":  # route mode skips these per method (SKIP_ROUTES) instead
        zap("ascan/action/excludeFromScan", regex=rf".*/users/{re.escape(dni)}/?(\?.*)?$")
        zap("ascan/action/excludeFromScan", regex=r".*/auth/reset-password/?.*")
    exclude_param("pin")
    if SCAN_MODE == "tree":
        ids, notes = {"tree": zap("ascan/action/scan", url=BASE + SCOPE.get(role, ""), recurse="true",
                                  inScopeOnly="false")["scan"]}, []
    else:
        ids, notes, meta = start_route_scans(role, only)
    if not ids:
        raise RuntimeError(f"no route could be scanned as {role}: {notes}")
    wanted = {str(i) for i in ids.values()}
    begin = last = time.time()
    while True:
        mine = [x for x in zap("ascan/view/scans")["scans"] if str(x["id"]) in wanted]
        if len(mine) != len(wanted):
            raise RuntimeError(f"ZAP scans {sorted(wanted)} ({ids}) not all in ascan/view/scans: {mine}; "
                               f"all scans: {zap('ascan/view/scans')}")
        pct = sum(int(x["progress"]) for x in mine) // len(mine)
        reqs, alerts = sum(int(x["reqCount"]) for x in mine), sum(int(x["alertCount"]) for x in mine)
        secs = int(time.time() - begin)
        status_line(f"scan {role} {bar(pct)} {pct:3d}% {secs // 60:02d}:{secs % 60:02d} "
                    f"req {reqs} alerts {alerts} | {latest_request()}")
        if all(x["state"] == "FINISHED" or int(x["progress"]) >= 100 for x in mine):
            break
        if time.time() - last > 10 and not token_alive(tok):  # fuzzing can revoke the token early
            tok = refresh(tok, dni)
            set_bearer(tok["access_token"])
            last = time.time()
        if time.time() - last > max(30, int(tok.get("expires_in", 300)) // 2):  # renew at half the TTL
            tok = refresh(tok, dni)
            set_bearer(tok["access_token"])
            last = time.time()
        time.sleep(2)
    log(f"active scan ({role}, {SCAN_MODE}) finished in {secs // 60:02d}:{secs % 60:02d}: "
        f"{reqs} requests, {alerts} alerts, {len(ids)} scans")
    if SCAN_MODE == "routes":
        done = {str(x["id"]): x for x in mine}
        for key, sid in ids.items():
            COVER.setdefault(role, []).append({"key": key, "req": int(done[str(sid)]["reqCount"]),
                                               "alerts": int(done[str(sid)]["alertCount"]), "inj": meta[key]})
        for key, note in notes:
            COVER.setdefault(role, []).append({"key": key, "note": note})
        for key, sid in ids.items():
            vlog(f"  scanned:     {key:<58} req {done[str(sid)]['reqCount']:>5} alerts {done[str(sid)]['alertCount']}")
        for key, note in notes:
            vlog(f"  {note:<45} {key}")
        for key in (("GET /users/{dni}", "GET /users/{dni}/accounts") if os.getenv("ZAP_DEBUG") == "1" else ()):
            if key not in ids:
                continue
            try:
                for mid in zap("ascan/view/messagesIds", scanId=ids[key])["messagesIds"][:6]:
                    msg = zap("core/view/message", id=mid)["message"]
                    log(f"  sent by [{key}]: {msg['requestHeader'].splitlines()[0]} -> "
                        f"{msg['responseHeader'].splitlines()[0]}")
            except (requests.RequestException, KeyError, ValueError, IndexError) as e:
                log(f"[!] cannot list the messages of scan {ids[key]}: {e}")


ROUTE_IDS = ((r"ES\d{22}", "{iban}"), (r"(?:USER|ACC|CARD)-[0-9A-F]+", "{id}"),
             (r"\b\d{16}\b", "{pan}"), (r"\d{8}[A-Z]", "{dni}"))


def route_key(method, path):
    """('GET', '/users/11111111H/cards/') -> 'GET /users/{dni}/cards'."""
    for pattern, name in ROUTE_IDS:
        path = re.sub(pattern, name, path)
    return f"{method} {path.rstrip('/') or '/'}"


def message_count():
    return int(zap("core/view/numberOfMessages", baseurl=BASE)["numberOfMessages"])


def in_scope(role, route):
    """True when `route` ('GET /admin/users') belongs to what `role` attacks (see SCOPE)."""
    path = route.split(" ", 1)[1]
    if role == "disposable":
        return path in ("/users/{dni}", "/auth/reset-password")
    if role in SCOPE:
        return path.startswith(SCOPE[role])
    return not path.startswith(("/admin", "/operations"))


def status_report(first=0, role=SCAN_AS, page=500):
    """Summarise what ZAP recorded from message `first` on (the scan phase): status codes, the
    app's own routes (those the seed used) that never answered 2xx/3xx, and server errors."""
    known = {route_key(*label.split(" ", 1)) for label, *_ in RESULTS if " " in label}
    known = {k for k in known | AUTH_FLOW if in_scope(role, k)}
    codes, routes, probes, examples, start = Counter(), {}, 0, {}, first
    history, first401, by401 = deque(maxlen=8), None, Counter()
    sample, app401, fivexx = {}, 0, Counter()
    while True:
        messages = zap("core/view/messages", baseurl=BASE, start=start, count=page)["messages"]
        for m in messages:
            parts = m["responseHeader"].split(" ", 2)
            code = parts[1].split()[0] if len(parts) > 1 and parts[1].split() else "none"
            codes[code] += 1
            method, url = (m["requestHeader"].split(" ", 2) + ["", ""])[:2]
            key = route_key(method, urlparse(url).path)
            line = (f"#{m.get('id')} {time.strftime('%H:%M:%S', time.gmtime(int(m['timestamp']) / 1000))}Z "
                    f"{method} {url.replace(BASE, '')} -> {code}")
            if code == "401":
                by401[key] += 1
                if not key.split(" ", 1)[1].startswith("/o/"):  # /o/ 401s are fuzzed clients, not a lost token
                    app401 += 1
                    if first401 is None:
                        first401 = [*history, line]  # the requests right before the first token 401
            history.append(line)
            if key in known:
                routes.setdefault(key, Counter())[code] += 1
                if code[0] not in "23":
                    sample.setdefault(key, f"{method} {url.replace(BASE, '')} -> {code} {m['responseBody'][:70]!r}")
            else:
                probes += 1  # ZAP forced browsing, trailing slashes, random ids...
            if code[0] in "50n":  # 5xx, "0" (no answer) or unparsable
                if code[0] == "5":
                    fivexx[key] += 1
                examples.setdefault(f"{code} {key}", []).append(
                    f"{method} {url.replace(BASE, '')} body={m['requestBody'][:80]!r} "
                    f"-> {m['responseBody'][:80]!r}")
        if len(messages) < page:
            break
        start += page
    log("responses by status:", dict(codes.most_common()))
    total = max(sum(codes.values()), 1)
    for code, problem in (("401", "the scan may have lost its token"),
                          ("429", "the lockout is absorbing the attacks")):
        share = codes[code] / total
        if share > WARN_SHARE:
            log(f"[!] {share:.0%} of the responses were {code}: {problem}, "
                "so treat 'no alerts' with caution")
    reached = {r for r, c in routes.items() if any(code[0] in "23" for code in c)}
    log(f"app routes answering 2xx/3xx during the scan: {len(reached)}/{len(known)} "
        f"(scanned as {role}); {probes} requests to unknown paths ignored")
    for route in sorted(known & reached):
        vlog(f"  ok:          {route:<58} {dict(routes[route].most_common(3))}")
    for route in sorted(known - reached):
        seen = dict(routes.get(route, Counter()).most_common(3)) or "never requested"
        vlog(f"  no OK answer: {route:<58} {seen}")
        if route in sample:
            vlog(f"      e.g. {sample[route]}")
    for code, rows in examples.items():
        log(f"  status {code} e.g.: " + " | ".join(dict.fromkeys(rows[:3])))
    if by401:
        log("  401 by route:", dict(by401.most_common(6)))
    if first401:
        log("  first 401 and the requests before it (UTC, ZAP message ids):")
        for line in first401:
            log("    " + line)
    STATS[role] = {"total": total, "app401": app401, "c429": codes["429"],
                   "routes": {k: set(c) for k, c in routes.items()}, "fivexx": dict(fivexx)}


def report():
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    r = z.get(f"{ZAP}/OTHER/core/other/htmlreport/", params={"apikey": ZAP_KEY}, timeout=120)
    r.raise_for_status()
    REPORT.write_text(r.text, encoding="utf-8")
    log("alerts:", zap("alert/view/alertsSummary", baseurl=BASE)["alertsSummary"])
    log(f"report: {REPORT}")


MIN_REQ = 50          # attack requests a route with injectable input must receive
MAX_LOST_401 = 0.02   # share of 401s outside /o/ (the scan lost its token) above which the scan is not valid
HANDLED = {"400", "403", "409", "422"}  # the request reached the app's logic with a valid session
DISPOSABLE_ORDER = ["GET /users/{dni}", "POST /auth/reset-password", "PATCH /users/{dni}", "DELETE /users/{dni}"]


def handled(codes):
    return any(c[0] in "23" or c in HANDLED for c in codes)


def verdict(roles):
    """One block that says whether the scan was good enough and, if not, why. True when it was."""
    blockers, limits, findings, errors5 = [], [], [], []
    log("\n" + "=" * 26 + " SCAN VERDICT " + "=" * 26)
    log(f"{'role':<12}{'routes':>7}{'w/input':>8}{'reached':>8}{'401 lost':>10}{'429':>7}{'requests':>10}")
    for role in roles:
        rows, st = COVER.get(role, []), STATS.get(role)
        if not rows or st is None:
            blockers.append(f"[{role}] no per-route scan data (role not scanned, or SCAN_MODE=tree)")
            continue
        scanned = [r for r in rows if "req" in r]
        inject = [r for r in scanned if r["inj"]]
        reached = [r for r in inject if handled(st["routes"].get(r["key"], ()))]
        total = max(st["total"], 1)
        log(f"{role:<12}{len(rows):>7}{len(inject):>8}{len(reached):>8}{st['app401'] / total:>10.1%}"
            f"{st['c429'] / total:>7.1%}{sum(r['req'] for r in scanned):>10}")
        errors5 += [f"[{role}] {n:>4} x {key}" for key, n in sorted(st.get("fivexx", {}).items(), key=lambda kv: -kv[1])]
        if st["app401"] / total > MAX_LOST_401:
            blockers.append(f"[{role}] {st['app401']} responses were 401 outside /o/: the token was lost, "
                            "so 'no alerts' proves nothing")
        if st["c429"] / total > WARN_SHARE:
            (limits if role == "disposable" else blockers).append(
                f"[{role}] {st['c429']} responses were 429: the PIN lockout (5 wrong PINs) absorbed part of the attacks")
        for r in rows:
            seen = sorted(st["routes"].get(r["key"], ()))
            if "note" in r:
                (blockers if r["note"].startswith("NOT STARTED") else limits).append(f"[{role}] {r['key']}: {r['note']}")
            elif not r["inj"]:
                limits.append(f"[{role}] {r['key']}: nothing to inject (path-only, or only `pin`, which is "
                              f"excluded to avoid the lockout); {r['req']} probes")
            elif not handled(seen):
                blockers.append(f"[{role}] {r['key']}: attacks never reached the app logic, codes seen {seen}")
            elif r["req"] < MIN_REQ:
                blockers.append(f"[{role}] {r['key']}: only {r['req']} attack requests (< {MIN_REQ})")
    refused = sum(1 for *_, status, expect in AUTHZ if status in expect)
    log(f"authorization matrix (direct requests): {refused}/{len(AUTHZ)} refused as expected")
    findings += [f"{who}: {method} {path} -> {status}, expected {expect}"
                 for who, method, path, status, expect in AUTHZ if status not in expect]
    if not AUTHZ:
        blockers.append("authorization matrix did not run")
    try:
        alerts = zap("alert/view/alerts", baseurl=BASE, start=0, count=5000)["alerts"]
        groups = Counter((a["risk"], a.get("alert") or a.get("name")) for a in alerts
                         if a["risk"] in ("High", "Medium", "Low"))
        log(f"alerts to triage (High/Medium/Low, passive and active): {sum(groups.values())}")
        for (risk, name), n in sorted(groups.items(), key=lambda g: ("High", "Medium", "Low").index(g[0][0])):
            log(f"  {risk:<7}{n:>4}  {name}")
    except (requests.RequestException, KeyError, ValueError) as e:
        log(f"[!] could not read the alerts: {e}")
    if errors5:
        log("server errors (5xx), known issue B9 in docs/vulnerability-inventory.md:")
        for text_ in errors5:
            log("  " + text_)
    for text_ in blockers:
        log("  BLOCKER  " + text_)
    for text_ in findings:
        log("  FINDING  " + text_)
    for text_ in limits:
        log("  limit    " + text_)
    missing = [r for r in ("customer", "auditor", "operations", "admin", "disposable") if r not in roles]
    log("COVERAGE: " + ("SUFFICIENT (no blockers; limits above go in the report)" if not blockers
                        else f"INSUFFICIENT, {len(blockers)} blocker(s) above")
        + (f" - PARTIAL RUN, not scanned: {', '.join(missing)} (unset SCAN_AS)" if missing else ""))
    log("AUTHZ:    " + ("all refused as expected" if not findings else f"{len(findings)} FINDING(S) above"))
    return not blockers and not missing


if __name__ == "__main__":
    reset_zap()
    restart_backend()
    delete_users_by_dni(STALE_DNIS)
    snapshot = snapshot_data()
    try:
        tokens = seed()
        SEED_END = message_count()  # the seed traffic in ZAP's history: scan targets come from it
        if not summary() and not ALLOW_FAILURES:
            sys.exit("aborted before scanning: fix the FAIL steps above (ALLOW_FAILURES=1 to scan anyway)")
        if os.getenv("SEED_ONLY") == "1":
            sys.exit(0)
        authz_check(tokens)
        # least to most destructive: the admin pass can delete or re-password other users
        order = ["customer", "auditor", "operations", "admin", "disposable"]
        roles = [r for r in order if r in tokens] if SCAN_AS == "all" else [SCAN_AS]
        for role in roles:
            if role not in tokens:
                sys.exit(f"cannot scan as {role}: no token (no role assigned or login failed)")
        log("roles to scan: " + ", ".join(roles))
        for role in roles:
            tok = refresh(tokens[role], SCAN_DNI[role])  # seed tokens expire (5 min TTL)
            mark = message_count()
            if role == "disposable":
                for key in DISPOSABLE_ORDER:  # one route at a time: each of them can destroy the user
                    restart_backend()  # clears the PIN lockout counters the previous route left behind
                    tok = refresh(tok, SCAN_DNI[role])
                    try:
                        scan(tok, role, only=key)
                    except RuntimeError as e:  # keep going: the report and verdict must still be produced
                        log(f"[!] disposable pass '{key}' aborted: {e}")
                        COVER.setdefault(role, []).append({"key": key, "note": f"NOT STARTED: aborted, {str(e)[:120]}"})
            else:
                scan(tok, role)
            status_report(mark, role)
            token_state(SCAN_DNI[role])
        report()
        if not verdict(roles):
            sys.exit(2)
    finally:
        clear_bearer()
        purge_new_data(snapshot)

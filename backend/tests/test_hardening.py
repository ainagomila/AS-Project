import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.test import Client

from banking.models import Account, Card

from .conftest import DNI_A, PASSWORD, PIN

pytestmark = pytest.mark.django_db

BACKEND = Path(__file__).resolve().parents[1]
PROD_ENV = {
    "DJANGO_SECRET_KEY": "x" * 60 + "-not-a-real-key-but-long-and-random-enough",
    "POSTGRES_PASSWORD": "db-secret",
    "DJANGO_ALLOWED_HOSTS": "localhost",
}


def _manage(*args, **env):
    """Run manage.py in a fresh process (no pytest, so no development fallbacks)."""
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "POSTGRES_"))}
    clean["DJANGO_SETTINGS_MODULE"] = "kofre.settings"
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=BACKEND, env={**clean, **env}, capture_output=True, text=True,
    )


# ---------------------------------------------------------------- settings

def test_without_debug_the_secret_key_is_required():
    result = _manage("check")
    assert result.returncode != 0
    assert "Set DJANGO_SECRET_KEY" in result.stderr


def test_debug_mode_uses_the_development_defaults():
    assert _manage("check", DJANGO_DEBUG="1").returncode == 0


def test_check_deploy_is_clean_in_a_production_like_config():
    result = _manage("check", "--deploy", "--fail-level", "WARNING", **PROD_ENV)
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------- headers

def test_security_headers_on_the_api(client, settings):
    settings.SECURE_HSTS_SECONDS = 31536000
    response = Client().get("/users", secure=True)
    assert response["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains; preload"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"] == "same-origin"
    assert "default-src 'none'" in response["Content-Security-Policy"]


def test_login_page_scripts_carry_the_csp_nonce():
    response = Client().get("/accounts/login/")
    policy = response["Content-Security-Policy"]
    nonce = policy.split("'nonce-")[1].split("'")[0]
    assert f"script-src 'nonce-{nonce}'" in policy
    assert "frame-ancestors 'none'" in policy
    html = response.content.decode()
    assert html.count(f'nonce="{nonce}"') == 2  # the inline <style> and <script>


# ---------------------------------------------------------------- lockout

def _fail_pin(client, url, times=5, **extra):
    for _ in range(times):
        assert client.post(url, {"pin": "000000", **extra}, format="json").status_code == 422


def test_verify_pin_locks_out_after_five_wrong_pins(ana):
    url = ana.url("/security/verify-pin")
    _fail_pin(ana.client, url)
    locked = ana.client.post(url, {"pin": PIN}, format="json")
    assert (locked.status_code, locked.json()["code"]) == (429, "TOO_MANY_ATTEMPTS")
    # Another client IP is not affected, nor are requests without a PIN.
    assert ana.client.post(url, {"pin": PIN}, format="json", REMOTE_ADDR="10.0.0.2").status_code == 200
    assert ana.client.get(ana.url()).status_code == 200


def test_reset_password_locks_out_per_dni(client, ana):
    body = {"dni": DNI_A, "newPassword": "Brand_New_1"}
    _fail_pin(client, "/auth/reset-password", **body)
    locked = client.post("/auth/reset-password", {**body, "pin": PIN}, format="json")
    assert locked.status_code == 429
    other_dni = client.post("/auth/reset-password", {**body, "dni": "87654321X", "pin": PIN}, format="json")
    assert other_dni.status_code == 422


def test_wrong_pins_on_any_endpoint_lock_verify_card(ana):
    _fail_pin(ana.client, ana.url("/security/verify-pin"), times=4)
    iban = ana.iban()
    Card.objects.create(
        id="CARD-1", pan="4111111111111111", expire_date="2029-05-31", alias="x", bank="Kofre",
        type="DEBIT", status="ACTIVE", pin="", account_id=Account.objects.get(iban=iban).id,
    )  # the policy hides a card that does not exist before the PIN is even checked
    url = ana.url(f"/accounts/{iban}/cards/4111111111111111/security/verify-card")
    assert ana.client.post(url, {"pin": "000000"}, format="json").status_code == 422
    assert ana.client.post(url, {"pin": PIN}, format="json").status_code == 429


def test_login_page_locks_out_after_five_wrong_passwords(ana):
    browser = Client()
    for _ in range(5):
        wrong = browser.post("/accounts/login/", {"username": DNI_A, "password": "Wrong_123"})
        assert wrong.status_code == 200
    locked = browser.post("/accounts/login/", {"username": DNI_A, "password": PASSWORD})
    assert locked.status_code == 429
    assert b"Too many failed attempts" in locked.content
    other_ip = Client(REMOTE_ADDR="10.0.0.2")
    assert other_ip.post("/accounts/login/", {"username": DNI_A, "password": PASSWORD}).status_code == 302

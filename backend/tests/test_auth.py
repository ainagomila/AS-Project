from datetime import timedelta

import pytest
from django.utils import timezone
from oauth2_provider.models import AccessToken

from banking.models import Account
from iam.models import User

from .conftest import DNI_A, DNI_B, PIN, register_payload

pytestmark = pytest.mark.django_db


def test_register_creates_user_and_initial_account(client):
    response = client.post("/auth/register", register_payload(), format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "User registered successfully"
    user = User.objects.get(dni=DNI_A)
    account = Account.objects.get(user_id=user.id)
    assert (account.name, account.bank, account.currency) == ("Kofre", "Kofre Bank", "EUR")


@pytest.mark.parametrize(
    "overrides, status, code",
    [
        ({"name": ""}, 400, "MISSING_FIELDS"),
        ({"dni": " "}, 400, "INVALID_DNI_FORMAT"),
        ({"dni": "12345678A"}, 400, "INVALID_DNI_FORMAT"),
        ({"email": "not-an-email"}, 400, "INVALID_EMAIL_FORMAT"),
        ({"phone": "600123456"}, 400, "INVALID_PHONE_FORMAT"),
        ({"password": "weak"}, 400, "INVALID_PASSWORD_FORMAT"),
        ({"pin": "12"}, 400, "DOMAIN_ERROR"),
        ({"pin": ""}, 400, "INVALID_PIN_FORMAT"),
        ({"gender": "robot"}, 400, "DOMAIN_ERROR"),
    ],
)
def test_register_validation_errors(client, overrides, status, code):
    response = client.post("/auth/register", register_payload(**overrides), format="json")
    assert response.status_code == status
    assert response.json()["code"] == code
    assert set(response.json()) == {"code", "message", "metadata"}


def test_register_duplicates(client, ana):
    same_dni = client.post("/auth/register", register_payload(phone="+34611111111"), format="json")
    same_phone = client.post("/auth/register", register_payload(dni=DNI_B), format="json")
    assert (same_dni.status_code, same_dni.json()["code"]) == (409, "USER_ALREADY_EXISTS")
    assert (same_phone.status_code, same_phone.json()["code"]) == (409, "USER_ALREADY_EXISTS")


def test_exists(client, ana):
    found = client.get(f"/auth/exists/{DNI_A}")
    assert (found.status_code, found.json()) == (200, True)
    missing = client.get(f"/auth/exists/{DNI_B}")
    assert (missing.status_code, missing.json()["code"]) == (404, "USER_NOT_FOUND")


def test_reset_password_with_pin(client, ana):
    body = {"dni": DNI_A, "pin": PIN, "newPassword": "Brand_New_1"}
    assert client.post("/auth/reset-password", body, format="json").status_code == 204
    assert User.objects.get(dni=DNI_A).check_password("Brand_New_1")

    wrong_pin = client.post("/auth/reset-password", {**body, "pin": "000000"}, format="json")
    weak = client.post("/auth/reset-password", {**body, "newPassword": "weak"}, format="json")
    unknown = client.post("/auth/reset-password", {**body, "dni": DNI_B}, format="json")
    assert (wrong_pin.status_code, wrong_pin.json()["code"]) == (422, "INVALID_PIN")
    assert (weak.status_code, weak.json()["code"]) == (400, "INVALID_PASSWORD_FORMAT")
    assert (unknown.status_code, unknown.json()["code"]) == (404, "USER_NOT_FOUND")


def test_protected_routes_need_a_matching_live_token(client, ana, bob):
    assert client.get(ana.url()).status_code == 401
    assert client.get(ana.url(), HTTP_AUTHORIZATION="Token abc").status_code == 401
    assert client.get(ana.url(), HTTP_AUTHORIZATION="Bearer nope").status_code == 401
    other = bob.client.get(ana.url())
    assert (other.status_code, other.content) == (401, b"")

    AccessToken.objects.filter(token=ana.token).update(expires=timezone.now() - timedelta(seconds=1))
    assert ana.client.get(ana.url()).status_code == 401

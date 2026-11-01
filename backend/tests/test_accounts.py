import pytest

from .conftest import PIN

pytestmark = pytest.mark.django_db

IBAN = "ES9121000418450200051332"
NEW = {"iban": IBAN, "name": "Cuenta ahorro", "bank": "CaixaBank", "balance": 100.5, "currency": "EUR"}


def test_list_has_initial_account(ana):
    response = ana.client.get(ana.url("/accounts"))
    assert response.status_code == 200
    (account,) = response.json()["accounts"]
    assert account == {
        "iban": account["iban"],
        "bank": "Kofre Bank",
        "name": "Kofre",
        "balance": 100.0,
        "currency": "EUR",
    }


def test_create_get_rename_delete(ana):
    created = ana.client.post(ana.url("/accounts"), NEW, format="json")
    assert created.status_code == 201
    assert created.json() == {**NEW, "balance": 100.5}

    url = ana.url(f"/accounts/{IBAN}")
    assert ana.client.get(url).json()["balance"] == 100.5

    renamed = ana.client.patch(url, {"name": "Ahorro viaje"}, format="json")
    assert (renamed.status_code, renamed.json()["name"]) == (200, "Ahorro viaje")

    wrong_pin = ana.client.delete(url, {"pin": "000000"}, format="json")
    no_pin = ana.client.delete(url, {}, format="json")
    assert (wrong_pin.status_code, wrong_pin.json()["code"]) == (422, "INVALID_PIN")
    assert (no_pin.status_code, no_pin.json()["code"]) == (400, "INVALID_PIN_FORMAT")
    assert ana.client.delete(url, {"pin": PIN}, format="json").status_code == 204
    gone = ana.client.get(url)
    assert (gone.status_code, gone.json()["code"]) == (404, "ACCOUNT_NOT_FOUND")


@pytest.mark.parametrize(
    "overrides, status, code",
    [
        ({"name": " "}, 422, "APPLICATION_ERROR"),
        ({"bank": ""}, 404, "BANK_NOT_FOUND"),
        ({"iban": "ES0000000000000000000000"}, 400, "INVALID_IBAN_FORMAT"),
        ({"balance": -1}, 400, "DOMAIN_ERROR"),
    ],
)
def test_create_errors(ana, overrides, status, code):
    response = ana.client.post(ana.url("/accounts"), {**NEW, **overrides}, format="json")
    assert (response.status_code, response.json()["code"]) == (status, code)


def test_duplicate_iban(ana):
    ana.client.post(ana.url("/accounts"), NEW, format="json")
    again = ana.client.post(ana.url("/accounts"), NEW, format="json")
    assert (again.status_code, again.json()["code"]) == (409, "ACCOUNT_ALREADY_EXISTS")


def test_rename_needs_a_name(ana):
    response = ana.client.patch(ana.url(f"/accounts/{ana.iban()}"), {"name": ""}, format="json")
    assert (response.status_code, response.json()["code"]) == (422, "APPLICATION_ERROR")


def test_other_users_account_looks_like_a_missing_one(ana, bob):
    foreign = ana.client.get(ana.url(f"/accounts/{bob.iban()}"))
    missing = ana.client.get(ana.url("/accounts/ES9121000418450200051332"))
    assert (foreign.status_code, foreign.json()) == (missing.status_code, missing.json())
    assert (foreign.status_code, foreign.json()["code"]) == (404, "ACCOUNT_NOT_FOUND")

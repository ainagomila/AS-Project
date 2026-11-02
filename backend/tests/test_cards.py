import pytest

from banking import card_services
from banking.models import Card
from common.errors import AppError

from .conftest import PIN

pytestmark = pytest.mark.django_db

PAN = "4111111111111111"


@pytest.fixture(autouse=True)
def verifier(monkeypatch):
    """Stand-in for the verifier service: accepts CVV 123 only."""
    monkeypatch.setattr(
        card_services, "verifier_accepts", lambda pan, expire, cvv: cvv == "123"
    )

NEW = {
    "pan": "4111 1111 1111 1111",
    "expireDate": "05/29",
    "alias": "Travel",
    "cvv": "123",
    "pin": "1234",
    "type": "debit",
    "bank": "BBVA",
}


@pytest.fixture
def card(ana):
    iban = ana.iban()
    response = ana.client.post(ana.url(f"/accounts/{iban}/cards"), NEW, format="json")
    assert response.status_code == 201, response.content
    return iban, response.json()


def test_create_card(ana, card):
    iban, body = card
    assert body == {
        "pan": PAN,
        "iban": iban,
        "alias": "Travel",
        "bank": "BBVA",
        "type": "DEBIT",
        "status": "ACTIVE",
        "expiryDate": "05/29",
    }
    stored = Card.objects.find_by_pan(NEW["pan"])
    assert (stored.pan, stored.pin) == (PAN, "1234")
    assert PAN not in stored.pan_enc and "1234" not in stored.pin_enc


def test_lists_and_detail(ana, card):
    iban, body = card
    assert ana.client.get(ana.url("/cards")).json() == {"cards": [body]}
    assert ana.client.get(ana.url(f"/accounts/{iban}/cards")).json() == {"cards": [body]}
    assert ana.client.get(ana.url(f"/accounts/{iban}/cards/{PAN}")).json() == body


@pytest.mark.parametrize(
    "overrides, status, code",
    [
        ({"pan": " "}, 400, "INVALID_PAN_FORMAT"),
        ({"pin": "123456"}, 400, "INVALID_PIN_FORMAT"),
        ({"cvv": "12"}, 400, "INVALID_CVV_FORMAT"),
        ({"bank": ""}, 404, "BANK_NOT_FOUND"),
        ({"type": "PREPAID"}, 400, "INVALID_TYPE_FORMAT"),
    ],
)
def test_create_errors(ana, overrides, status, code):
    url = ana.url(f"/accounts/{ana.iban()}/cards")
    response = ana.client.post(url, {**NEW, **overrides}, format="json")
    assert (response.status_code, response.json()["code"]) == (status, code)


def test_duplicate_pan_and_bad_expiry(ana, card):
    url = ana.url(f"/accounts/{card[0]}/cards")
    again = ana.client.post(url, NEW, format="json")
    assert (again.status_code, again.json()["code"]) == (409, "CARD_ALREADY_EXISTS")
    bad_expiry = ana.client.post(url, {**NEW, "pan": "5500000000000004", "expireDate": "soon"}, format="json")
    assert bad_expiry.status_code == 500


def test_update_alias_and_status(ana, card):
    url = ana.url(f"/accounts/{card[0]}/cards/{PAN}")
    alias = ana.client.patch(url, {"alias": "Viajes"}, format="json")
    assert (alias.status_code, alias.json()["alias"]) == (200, "Viajes")
    frozen = ana.client.patch(url, {"status": "FREEZED"}, format="json")
    assert (frozen.status_code, frozen.json()["status"]) == (200, "FREEZED")
    invalid = ana.client.patch(url, {"status": "FROZEN"}, format="json")
    assert (invalid.status_code, invalid.json()["code"]) == (422, "APPLICATION_ERROR")


def test_verify_card_never_returns_the_card_pin_or_cvv(ana, card):
    url = ana.url(f"/accounts/{card[0]}/cards/{PAN}/security/verify-card")
    ok = ana.client.post(url, {"pin": PIN}, format="json")
    assert (ok.status_code, ok.json()) == (200, {"pan": PAN, "expireDate": "05/29"})
    wrong = ana.client.post(url, {"pin": "000000"}, format="json")
    missing = ana.client.post(url, {}, format="json")
    assert (wrong.status_code, wrong.json()["code"]) == (422, "INVALID_PIN")
    assert (missing.status_code, missing.json()["code"]) == (400, "INVALID_PIN_FORMAT")


def test_delete_card(ana, card):
    url = ana.url(f"/accounts/{card[0]}/cards/{PAN}")
    wrong = ana.client.delete(url, {"pin": "000000"}, format="json")
    assert (wrong.status_code, wrong.json()["code"]) == (422, "INVALID_PIN")
    assert ana.client.delete(url, {"pin": PIN}, format="json").status_code == 204
    gone = ana.client.get(url)
    assert (gone.status_code, gone.json()["code"]) == (404, "CARD_NOT_FOUND")


def test_card_on_another_users_account(ana, bob, card):
    other = ana.client.post(ana.url(f"/accounts/{bob.iban()}/cards"), {**NEW, "pan": "5500000000000004"}, format="json")
    assert (other.status_code, other.json()["code"]) == (404, "ACCOUNT_NOT_FOUND")
    # A real card reached through the wrong account answers like a missing card.
    wrong_account = bob.client.get(bob.url(f"/accounts/{bob.iban()}/cards/{PAN}"))
    missing = bob.client.get(bob.url(f"/accounts/{bob.iban()}/cards/5500000000000004"))
    assert (wrong_account.status_code, wrong_account.json()) == (missing.status_code, missing.json())
    assert (wrong_account.status_code, wrong_account.json()["code"]) == (404, "CARD_NOT_FOUND")


def test_wrong_cvv_is_rejected_by_the_verifier(ana):
    body = {**NEW, "cvv": "999"}
    response = ana.client.post(ana.url(f"/accounts/{ana.iban()}/cards"), body, format="json")
    assert (response.status_code, response.json()["code"]) == (400, "INVALID_CARD")
    assert not Card.objects.exists()


def test_verifier_down_is_an_infra_error(ana, monkeypatch):
    def down(*args):
        raise AppError("INFRA_ERROR", "Servei de verificació no disponible")

    monkeypatch.setattr(card_services, "verifier_accepts", down)
    response = ana.client.post(ana.url(f"/accounts/{ana.iban()}/cards"), NEW, format="json")
    assert response.status_code == 500
    assert not Card.objects.exists()

import pytest

from payments.models import Payment

from .conftest import PIN

pytestmark = pytest.mark.django_db


def transfer(actor, destination, **overrides):
    body = {
        "beneficiary": "Lea Johnson",
        "destinationIban": destination,
        "amount": 25.5,
        "currency": "EUR",
        "concept": "Rent November",
        "categories": ["rent"],
        "pin": PIN,
    }
    body.update(overrides)
    return actor.client.post(actor.url(f"/accounts/{actor.iban()}/transfers"), body, format="json")


def balance(actor):
    return actor.client.get(actor.url("/accounts")).json()["accounts"][0]["balance"]


def history(actor, query=""):
    return actor.client.get(actor.url(f"/accounts/{actor.iban()}/transfers{query}")).json()["transfers"]


def test_transfer_moves_money_and_shows_on_both_sides(ana, bob):
    response = transfer(ana, bob.iban())
    assert (response.status_code, response.content) == (200, b"")
    assert (balance(ana), balance(bob)) == (74.5, 125.5)

    (sent,) = history(ana)
    (received,) = history(bob)
    assert sent == {
        "title": "Rent November",
        "date": sent["date"],
        "amount": -25.5,
        "currency": "EUR",
        "categories": ["RENT"],
    }
    assert sent["date"].endswith("Z")
    assert received["amount"] == 25.5
    payment = Payment.objects.get()
    assert (payment.type, payment.status) == ("BANK_TRANSFER", "COMPLETED")


@pytest.mark.parametrize(
    "overrides, status, code",
    [
        ({"pin": "000000"}, 422, "INVALID_PIN"),
        ({"pin": None}, 400, "INVALID_PIN_FORMAT"),
        ({"beneficiary": ""}, 422, "APPLICATION_ERROR"),
        ({"destinationIban": "ES00"}, 400, "INVALID_IBAN_FORMAT"),
        ({"destinationIban": "ES9121000418450200051332"}, 404, "ACCOUNT_NOT_FOUND"),
        ({"amount": 0}, 400, "DOMAIN_ERROR"),
        ({"amount": 1000}, 422, "INSUFFICIENT_FUNDS"),
        ({"currency": ""}, 400, "DOMAIN_ERROR"),
        ({"currency": "USD"}, 400, "DOMAIN_ERROR"),
        ({"concept": " "}, 422, "APPLICATION_ERROR"),
        ({"categories": ["TRICOUNT"]}, 400, "DOMAIN_ERROR"),
    ],
)
def test_transfer_errors(ana, bob, overrides, status, code):
    response = transfer(ana, bob.iban(), **overrides)
    assert (response.status_code, response.json()["code"]) == (status, code)
    assert balance(ana) == 100.0


def test_cannot_transfer_from_someone_elses_account(ana, bob):
    response = ana.client.post(
        ana.url(f"/accounts/{bob.iban()}/transfers"),
        {"beneficiary": "x", "destinationIban": ana.iban(), "amount": 5, "currency": "EUR", "concept": "x", "pin": PIN},
        format="json",
    )
    assert (response.status_code, response.json()["code"]) == (403, "UNAUTHORIZED")


def test_history_filters_and_sorting(ana, bob):
    transfer(ana, bob.iban(), concept="Bravo", amount=1)
    transfer(ana, bob.iban(), concept="alpha", amount=2)
    transfer(bob, ana.iban(), concept="Charlie", amount=3)

    assert [t["title"] for t in history(ana, "?sort=alpha,asc")] == ["alpha", "Bravo", "Charlie"]
    assert [t["title"] for t in history(ana, "?sort=alpha,desc")] == ["Charlie", "Bravo", "alpha"]
    assert [t["title"] for t in history(ana, "?q=RAV")] == ["Bravo"]
    assert {t["title"] for t in history(ana, "?onlyExpenses=true")} == {"Bravo", "alpha"}

    today = history(ana)[0]["date"][:10]
    assert len(history(ana, f"?from={today}&to={today}")) == 3
    assert history(ana, "?to=2000-01-01") == []
    assert history(ana, "?from=2999-01-01") == []

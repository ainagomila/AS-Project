import pytest
from django.core.management import CommandError, call_command

from iam.models import User

from .conftest import DNI_A, DNI_B, PIN

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(ana):
    call_command("create_admin", DNI_A)
    return ana


def test_create_admin_needs_an_existing_user(db):
    with pytest.raises(CommandError):
        call_command("create_admin", DNI_B)


def test_admin_flag_is_reported(admin):
    assert admin.client.get(admin.url()).json()["admin"] is True


def test_non_admin_is_refused_everywhere(ana, bob):
    iban = bob.iban()
    responses = [
        ana.client.get("/admin/users"),
        ana.client.get(f"/admin/users/{DNI_B}/accounts"),
        ana.client.get(f"/admin/users/{DNI_B}/accounts/{iban}/transfers"),
        ana.client.patch(f"/admin/users/{DNI_B}", {"active": False}, format="json"),
    ]
    assert [(r.status_code, r.json()["code"]) for r in responses] == [(403, "FORBIDDEN")] * 4
    assert User.objects.get(dni=DNI_B).is_active


def test_admin_routes_need_a_token(client, bob):
    assert client.get("/admin/users").status_code == 401
    assert client.get(f"/admin/users/{DNI_B}/accounts").status_code == 401


def test_admin_can_list_and_drill_down(admin, bob):
    users = admin.client.get("/admin/users").json()
    assert {(u["dni"], u["active"], u["admin"]) for u in users} == {(DNI_A, True, True), (DNI_B, True, False)}

    iban = bob.iban()
    accounts = admin.client.get(f"/admin/users/{DNI_B}/accounts").json()["accounts"]
    assert [a["iban"] for a in accounts] == [iban]

    bob.client.post(
        bob.url(f"/accounts/{iban}/transfers"),
        {"beneficiary": "Ana", "destinationIban": admin.iban(), "amount": 10, "currency": "EUR", "concept": "Gift", "pin": PIN},
        format="json",
    )
    transfers = admin.client.get(f"/admin/users/{DNI_B}/accounts/{iban}/transfers").json()["transfers"]
    assert [(t["title"], t["amount"]) for t in transfers] == [("Gift", -10.0)]

    unknown_user = admin.client.get("/admin/users/00000000T/accounts")
    foreign_account = admin.client.get(f"/admin/users/{DNI_B}/accounts/{admin.iban()}/transfers")
    assert (unknown_user.status_code, unknown_user.json()["code"]) == (404, "USER_NOT_FOUND")
    assert (foreign_account.status_code, foreign_account.json()["code"]) == (404, "ACCOUNT_NOT_FOUND")


def test_disable_and_enable_user(admin, bob):
    bad = admin.client.patch(f"/admin/users/{DNI_B}", {"active": "no"}, format="json")
    assert (bad.status_code, bad.json()["code"]) == (400, "MISSING_FIELDS")

    disabled = admin.client.patch(f"/admin/users/{DNI_B}", {"active": False}, format="json")
    assert (disabled.status_code, disabled.json()["active"]) == (200, False)

    # Disabling ends the user's sessions: the old token is dead even after re-enabling.
    assert bob.client.get(bob.url()).status_code == 401

    admin.client.patch(f"/admin/users/{DNI_B}", {"active": True}, format="json")
    assert bob.client.get(bob.url()).status_code == 401

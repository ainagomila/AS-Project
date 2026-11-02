import pytest
from django.core.management import call_command

from banking.models import Account, Card
from iam import admin_services
from iam import system_settings
from iam.models import AuditLog, Role, SystemSetting, User
from payments.models import Payment
from common.errors import AppError

from .conftest import DNI_A, DNI_B, PASSWORD, PIN

pytestmark = pytest.mark.django_db

DNI_C = "11111111H"
NEW_USER = {
    "name": "Carlos Diaz",
    "dni": DNI_C,
    "email": "carlos@example.com",
    "phone": "+34611111111",
    "password": "Carlos_123",
    "birthdate": "1990-05-20",
    "gender": "male",
    "pin": "654321",
}


@pytest.fixture
def admin(ana):
    call_command("create_admin", DNI_A)
    return ana


@pytest.fixture
def auditor(bob):
    call_command("create_admin", DNI_B, role="AUDITOR")
    return bob


# ---------------------------------------------------------------- roles

def test_login_reports_role(client, admin, auditor):
    login = client.post("/auth/login", {"dni": DNI_A, "password": PASSWORD}, format="json")
    assert (login.json()["user"]["role"], login.json()["user"]["admin"]) == ("ADMIN", True)
    login = client.post("/auth/login", {"dni": DNI_B, "password": PASSWORD}, format="json")
    assert (login.json()["user"]["role"], login.json()["user"]["admin"]) == ("AUDITOR", False)


def test_auditor_can_read_but_not_write(auditor, bob, ana):
    reads = [
        auditor.client.get("/admin/users"),
        auditor.client.get("/admin/accounts"),
        auditor.client.get("/admin/cards"),
        auditor.client.get("/admin/transfers"),
        auditor.client.get("/admin/audit-logs"),
        auditor.client.get("/admin/settings"),
        auditor.client.get("/admin/stats"),
        auditor.client.get(f"/admin/users/{DNI_A}/accounts"),
        auditor.client.get(f"/admin/users/{DNI_A}/cards"),
    ]
    assert all(r.status_code == 200 for r in reads), [r.status_code for r in reads]

    writes = [
        auditor.client.post("/admin/users", NEW_USER, format="json"),
        auditor.client.patch(f"/admin/users/{DNI_A}", {"active": False}, format="json"),
        auditor.client.delete(f"/admin/users/{DNI_A}"),
        auditor.client.patch(f"/admin/accounts/{bob.iban()}", {"status": "FROZEN"}, format="json"),
        auditor.client.patch(f"/admin/settings/SESSION_TTL_SECONDS", {"value": 60}, format="json"),
    ]
    assert [(r.status_code, r.json()["code"]) for r in writes] == [(403, "FORBIDDEN")] * 5


def test_regular_user_cannot_access_admin(bob):
    assert bob.client.get("/admin/users").status_code == 403
    assert bob.client.get("/admin/accounts").status_code == 403


# ---------------------------------------------------------------- user management

def test_admin_can_create_user(admin):
    created = admin.client.post("/admin/users", NEW_USER, format="json")
    assert created.status_code == 201, created.content
    assert created.json()["role"] == "USER"
    user = User.objects.get(dni=DNI_C)
    assert Account.objects.filter(user_id=user.id).count() == 1

    with_auditor = admin.client.post(
        "/admin/users", {**NEW_USER, "dni": "22222222J", "role": "AUDITOR",
                         "email": "carla@example.com", "phone": "+34622222222"},
        format="json",
    )
    assert (with_auditor.status_code, with_auditor.json()["role"]) == (201, "AUDITOR")


def test_admin_update_role_and_active(admin, bob):
    promoted = admin.client.patch(f"/admin/users/{DNI_B}", {"role": "AUDITOR"}, format="json")
    assert (promoted.status_code, promoted.json()["role"]) == (200, "AUDITOR")

    disabled = admin.client.patch(f"/admin/users/{DNI_B}", {"active": False}, format="json")
    assert (disabled.status_code, disabled.json()["active"]) == (200, False)
    assert bob.client.get(bob.url()).json()["code"] == "USER_DISABLED"


def test_admin_cannot_modify_self(admin):
    self_patch = admin.client.patch(f"/admin/users/{DNI_A}", {"role": "USER"}, format="json")
    self_delete = admin.client.delete(f"/admin/users/{DNI_A}")
    assert (self_patch.status_code, self_patch.json()["code"]) == (409, "CANNOT_MODIFY_SELF")
    assert (self_delete.status_code, self_delete.json()["code"]) == (409, "CANNOT_MODIFY_SELF")
    assert User.objects.get(dni=DNI_A).role == Role.ADMIN


def test_last_admin_guard(admin, bob):
    someone = User.objects.get(dni=DNI_B)
    target = User.objects.get(dni=DNI_A)
    with pytest.raises(AppError) as exc:
        admin_services._guard_admin_removal(someone, target, Role.USER, True)
    assert exc.value.code == "LAST_ADMIN"


def test_admin_delete_user_cascades(admin, bob):
    iban = bob.iban()
    bob.client.post(
        bob.url(f"/accounts/{iban}/transfers"),
        {"beneficiary": "Ana", "destinationIban": admin.iban(), "amount": 5,
         "currency": "EUR", "concept": "Loan", "pin": PIN},
        format="json",
    )
    bob_id = User.objects.get(dni=DNI_B).id

    assert admin.client.delete(f"/admin/users/{DNI_B}").status_code == 204

    assert not User.objects.filter(dni=DNI_B).exists()
    assert not Account.objects.filter(user_id=bob_id).exists()
    assert not Card.objects.filter(account_id__in=Account.objects.filter(user_id=bob_id)).exists()
    assert Payment.objects.filter(emitter_id=iban).count() == 0


def test_admin_reset_password_revokes_sessions(admin, bob):
    assert admin.client.post(
        f"/admin/users/{DNI_B}/reset-password", {"newPassword": "Reset_4567"}, format="json"
    ).status_code == 200
    assert bob.client.get(bob.url()).status_code == 401
    login = admin.client.post("/auth/login", {"dni": DNI_B, "password": "Reset_4567"}, format="json")
    assert login.status_code == 200


# ---------------------------------------------------------------- accounts / cards

def test_freeze_account_blocks_transfers(admin, bob):
    iban = bob.iban()
    frozen = admin.client.patch(f"/admin/accounts/{iban}", {"status": "FROZEN"}, format="json")
    assert (frozen.status_code, frozen.json()["status"]) == (200, "FROZEN")

    transfer = bob.client.post(
        bob.url(f"/accounts/{iban}/transfers"),
        {"beneficiary": "Ana", "destinationIban": admin.iban(), "amount": 5,
         "currency": "EUR", "concept": "x", "pin": PIN},
        format="json",
    )
    assert (transfer.status_code, transfer.json()["code"]) == (422, "ACCOUNT_FROZEN")


def test_admin_can_block_and_delete_card(admin, bob):
    iban = bob.iban()
    card = bob.client.post(
        bob.url(f"/accounts/{iban}/cards"),
        {"pan": "4111111111111111", "expireDate": "05/29", "alias": "Travel",
         "cvv": "123", "pin": "1234", "type": "debit", "bank": "BBVA"},
        format="json",
    ).json()

    blocked = admin.client.patch(f"/admin/cards/{card['pan']}", {"status": "DEAD"}, format="json")
    assert (blocked.status_code, blocked.json()["status"]) == (200, "DEAD")
    assert admin.client.delete(f"/admin/cards/{card['pan']}").status_code == 204
    assert not Card.objects.filter(pan=card["pan"]).exists()


# ---------------------------------------------------------------- audit + settings

def test_audit_logs_record_admin_actions(admin):
    admin.client.post("/admin/users", NEW_USER, format="json")
    logs = admin.client.get("/admin/audit-logs").json()["auditLogs"]
    assert any(e["action"] == "user.create" and e["targetId"] == DNI_C for e in logs)


def test_settings_read_and_update(admin):
    settings = admin.client.get("/admin/settings").json()["settings"]
    keys = {s["key"] for s in settings}
    assert "SESSION_TTL_SECONDS" in keys and "MAINTENANCE_MODE" in keys

    updated = admin.client.patch(
        "/admin/settings/SESSION_TTL_SECONDS", {"value": 60}, format="json"
    )
    assert (updated.status_code, updated.json()["value"]) == (200, 60)

    unknown = admin.client.patch("/admin/settings/NOPE", {"value": 1}, format="json")
    invalid = admin.client.patch("/admin/settings/MAINTENANCE_MODE", {"value": "yes"}, format="json")
    assert (unknown.status_code, unknown.json()["code"]) == (404, "SETTING_NOT_FOUND")
    assert (invalid.status_code, invalid.json()["code"]) == (422, "APPLICATION_ERROR")


def test_registration_toggle(admin, client):
    admin.client.patch("/admin/settings/REGISTRATION_ENABLED", {"value": False}, format="json")
    response = client.post(
        "/auth/register",
        {**NEW_USER, "dni": "33333333X", "email": "d@example.com", "phone": "+34633333333"},
        format="json",
    )
    assert (response.status_code, response.json()["code"]) == (403, "REGISTRATION_DISABLED")


def test_transfer_max_amount(admin, bob):
    admin.client.patch("/admin/settings/TRANSFER_MAX_AMOUNT", {"value": 10}, format="json")
    transfer = bob.client.post(
        bob.url(f"/accounts/{bob.iban()}/transfers"),
        {"beneficiary": "Ana", "destinationIban": admin.iban(), "amount": 20,
         "currency": "EUR", "concept": "big", "pin": PIN},
        format="json",
    )
    assert (transfer.status_code, transfer.json()["code"]) == (400, "DOMAIN_ERROR")


def test_login_lockout(admin, bob, client):
    admin.client.patch("/admin/settings/LOGIN_MAX_ATTEMPTS", {"value": 3}, format="json")
    for _ in range(3):
        client.post("/auth/login", {"dni": DNI_B, "password": "Wrong_123"}, format="json")
    locked = client.post("/auth/login", {"dni": DNI_B, "password": PASSWORD}, format="json")
    assert (locked.status_code, locked.json()["code"]) == (423, "ACCOUNT_LOCKED")


def test_maintenance_mode(admin, bob):
    admin.client.patch("/admin/settings/MAINTENANCE_MODE", {"value": True}, format="json")
    transfer = bob.client.post(
        bob.url(f"/accounts/{bob.iban()}/transfers"),
        {"beneficiary": "Ana", "destinationIban": admin.iban(), "amount": 1,
         "currency": "EUR", "concept": "x", "pin": PIN},
        format="json",
    )
    assert (transfer.status_code, transfer.json()["code"]) == (503, "MAINTENANCE_MODE")
    assert admin.client.get("/admin/users").status_code == 200

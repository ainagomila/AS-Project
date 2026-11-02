"""Back office: administrator and auditor roles, enforced by the XACML policy."""

import pytest
from django.core.management import CommandError, call_command
from oauth2_provider.models import AccessToken

from authz.models import AuditEvent
from iam.models import User

from .conftest import DNI_A, DNI_B, PIN, Actor, register_payload

pytestmark = pytest.mark.django_db

DNI_C = "11111111H"


@pytest.fixture
def admin(ana):
    call_command("create_admin", DNI_A)
    return ana


@pytest.fixture
def auditor(db):
    actor = Actor(DNI_C, "+34600111111")
    call_command("set_role", DNI_C, "auditor")
    return actor


def user_id(dni):
    return User.objects.get_by_natural_key(dni).id


def account_id(dni):
    from banking.models import Account

    return Account.objects.get(user_id=user_id(dni)).id


def gift(sender, receiver_iban, amount=10):
    response = sender.client.post(
        sender.url(f"/accounts/{sender.iban()}/transfers"),
        {"beneficiary": "x", "destinationIban": receiver_iban, "amount": amount, "currency": "EUR",
         "concept": "Gift", "pin": PIN},
        format="json",
    )
    assert response.status_code == 200, response.content


# ------------------------------------------------------------------ roles

def test_role_commands_need_an_existing_user(db):
    with pytest.raises(CommandError):
        call_command("create_admin", DNI_B)
    with pytest.raises(CommandError):
        call_command("set_role", DNI_B, "auditor")


def test_profile_reports_the_role(admin, auditor):
    assert admin.client.get(admin.url()).json()["role"] == "admin"
    assert admin.client.get(admin.url()).json()["admin"] is True
    assert auditor.client.get(auditor.url()).json()["role"] == "auditor"


def test_customers_are_refused_everywhere_in_the_back_office(ana, bob):
    target, account = user_id(DNI_B), account_id(DNI_B)
    responses = [
        ana.client.get("/admin/users"),
        ana.client.get(f"/admin/users/{target}/accounts"),
        ana.client.get(f"/admin/users/{target}/accounts/{account}/transfers"),
        ana.client.patch(f"/admin/users/{target}", {"active": False}, format="json"),
        ana.client.get("/admin/audit"),
        ana.client.get("/admin/users/does-not-exist/accounts"),
    ]
    assert [(r.status_code, r.json()["code"]) for r in responses] == [(403, "FORBIDDEN")] * 6
    assert User.objects.get_by_natural_key(DNI_B).is_active


def test_back_office_needs_a_token(client, bob):
    assert client.get("/admin/users").status_code == 401
    assert client.get(f"/admin/users/{user_id(DNI_B)}/accounts").status_code == 401
    assert client.get("/admin/audit").status_code == 401


# ------------------------------------------------------------------ administrator

def test_admin_lists_users_without_unneeded_personal_data(admin, bob, auditor):
    users = admin.client.get("/admin/users").json()
    assert {(u["dni"], u["role"], u["active"]) for u in users} == {
        (DNI_A, "admin", True), (DNI_B, "customer", True), (DNI_C, "auditor", True),
    }
    assert set(users[0]) == {"id", "dni", "name", "email", "phone", "role", "active"}


def test_admin_disables_and_enables_a_customer(admin, bob):
    target = user_id(DNI_B)
    bad = admin.client.patch(f"/admin/users/{target}", {"active": "no"}, format="json")
    assert (bad.status_code, bad.json()["code"]) == (400, "MISSING_FIELDS")

    disabled = admin.client.patch(f"/admin/users/{target}", {"active": False}, format="json")
    assert (disabled.status_code, disabled.json()["active"]) == (200, False)
    # Disabling ends the user's sessions: the old token is dead even after re-enabling.
    assert bob.client.get(bob.url()).status_code == 401

    admin.client.patch(f"/admin/users/{target}", {"active": True}, format="json")
    assert bob.client.get(bob.url()).status_code == 401
    assert User.objects.get_by_natural_key(DNI_B).is_active


def test_admin_cannot_disable_staff_or_themselves(admin, bob, auditor):
    call_command("set_role", DNI_B, "admin")
    for dni in (DNI_A, DNI_B, DNI_C):
        response = admin.client.patch(f"/admin/users/{user_id(dni)}", {"active": False}, format="json")
        assert (response.status_code, response.json()["code"]) == (403, "FORBIDDEN")
        assert User.objects.get_by_natural_key(dni).is_active


def test_admin_does_not_see_money(admin, bob):
    """Separation of duties: identity management, not finances."""
    target, account = user_id(DNI_B), account_id(DNI_B)
    responses = [
        admin.client.get(f"/admin/users/{target}/accounts"),
        admin.client.get(f"/admin/users/{target}/accounts/{account}/transfers"),
        admin.client.get("/admin/audit"),
    ]
    assert [(r.status_code, r.json()["code"]) for r in responses] == [(403, "FORBIDDEN")] * 3


def test_unknown_target_user_looks_missing(admin):
    response = admin.client.patch("/admin/users/USER-NOPE", {"active": False}, format="json")
    assert (response.status_code, response.json()["code"]) == (404, "USER_NOT_FOUND")


def test_admin_manages_customer_lifecycle(admin, bob):
    payload = register_payload(
        dni="11111111H",
        phone="+34600111111",
        name="Created Customer",
        email="created@example.com",
    )
    created = admin.client.post("/admin/users", payload, format="json")
    assert created.status_code == 201, created.content
    target = User.objects.get_by_natural_key("11111111H")
    assert target.role == "customer"

    promoted = admin.client.patch(
        f"/admin/users/{target.id}", {"role": "auditor"}, format="json"
    )
    assert (promoted.status_code, promoted.json()["code"]) == (403, "FORBIDDEN")
    assert target.role == "customer"

    reset = admin.client.post(
        f"/admin/users/{User.objects.get_by_natural_key(DNI_B).id}",
        {"newPassword": "New_Admin_Reset_1"},
        format="json",
    )
    assert reset.status_code == 200
    assert User.objects.get_by_natural_key(DNI_B).check_password("New_Admin_Reset_1")

    deleted = admin.client.delete(f"/admin/users/{target.id}")
    assert deleted.status_code == 204
    assert not User.objects.filter(id=target.id).exists()

    bob_id = User.objects.get_by_natural_key(DNI_B).id
    deleted = admin.client.delete(f"/admin/users/{bob_id}")
    assert deleted.status_code == 204
    assert not User.objects.filter(id=bob_id).exists()


# ------------------------------------------------------------------ auditor

def test_auditor_sees_pseudonymised_users(auditor, bob):
    users = {u["id"]: u for u in auditor.client.get("/admin/users").json()}
    bob_row = users[user_id(DNI_B)]
    assert bob_row["dni"] == "*****321X"
    assert bob_row["name"] == "A. B."
    assert bob_row["email"].startswith("u***@")
    assert DNI_B not in str(users)


def test_auditor_follows_the_money_pseudonymised(auditor, ana, bob):
    gift(bob, ana.iban())
    target, account = user_id(DNI_B), account_id(DNI_B)

    accounts = auditor.client.get(f"/admin/users/{target}/accounts").json()["accounts"]
    assert [(a["id"], a["balance"]) for a in accounts] == [(account, 90.0)]
    iban = bob.iban()
    assert accounts[0]["iban"] == f"{iban[:4]} **** **** {iban[-4:]}"

    transfers = auditor.client.get(f"/admin/users/{target}/accounts/{account}/transfers").json()["transfers"]
    assert [(t["title"], t["amount"]) for t in transfers] == [("Gift", -10.0)]


def test_auditor_changes_nothing(auditor, bob):
    response = auditor.client.patch(f"/admin/users/{user_id(DNI_B)}", {"active": False}, format="json")
    assert (response.status_code, response.json()["code"]) == (403, "FORBIDDEN")
    assert User.objects.get_by_natural_key(DNI_B).is_active


def test_auditor_cannot_reach_an_account_through_another_user(auditor, ana, bob):
    response = auditor.client.get(f"/admin/users/{user_id(DNI_B)}/accounts/{account_id(DNI_A)}/transfers")
    assert (response.status_code, response.json()["code"]) == (404, "ACCOUNT_NOT_FOUND")


# ------------------------------------------------------------------ audit trail

def test_audit_trail_records_staff_actions_and_denials(admin, auditor, bob):
    admin.client.patch(f"/admin/users/{user_id(DNI_B)}", {"active": False}, format="json")
    admin.client.get(f"/admin/users/{user_id(DNI_B)}/accounts")  # denied: separation of duties

    events = auditor.client.get("/admin/audit").json()["events"]
    summary = [(e["subjectRole"], e["action"], e["decision"], e["status"]) for e in events]
    assert ("admin", "set-status", "Permit", 200) in summary
    assert ("admin", "list-accounts", "Deny", 403) in summary
    disabled = next(e for e in events if e["action"] == "set-status")
    assert (disabled["subjectId"], disabled["resourceId"]) == (user_id(DNI_A), user_id(DNI_B))
    assert disabled["rule"] == "urn:kofre:rule:admin-changes-customer-status"
    # Identities are recorded as internal ids only.
    assert DNI_A not in str(events) and DNI_B not in str(events)


def test_customer_money_movements_are_audited(ana, bob):
    gift(bob, ana.iban())
    event = AuditEvent.objects.get(action="transfer")
    assert (event.subject_id, event.decision, event.status_code) == (user_id(DNI_B), "Permit", 200)
    assert not AuditEvent.objects.filter(action="read").exists()  # plain reads are not logged


def test_audit_events_are_append_only(ana, bob):
    ana.client.get(bob.url())  # a denial, so there is an event
    event = AuditEvent.objects.get()
    with pytest.raises(PermissionError):
        event.save()
    with pytest.raises(PermissionError):
        event.delete()
    with pytest.raises(PermissionError):
        AuditEvent.objects.update(decision="Permit")
    with pytest.raises(PermissionError):
        AuditEvent.objects.all().delete()


# ------------------------------------------------------------------ session conditions

def test_disabled_user_is_refused_even_with_a_live_token(ana):
    User.objects.filter(pk=user_id(DNI_A)).update(is_active=False)
    response = ana.client.get(ana.url())
    assert (response.status_code, response.json()["code"]) == (403, "USER_DISABLED")


def test_token_without_banking_scope_is_refused(ana):
    AccessToken.objects.filter(token=ana.token).update(scope="openid")
    response = ana.client.get(ana.url())
    assert (response.status_code, response.json()["code"]) == (403, "FORBIDDEN")

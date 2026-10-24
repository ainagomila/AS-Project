import pytest

from banking.models import Account
from iam.models import Session, User

from .conftest import DNI_A, DNI_B, PASSWORD, PIN

pytestmark = pytest.mark.django_db


def test_get_profile(ana):
    response = ana.client.get(ana.url())
    assert response.status_code == 200
    assert set(response.json()) == {"dni", "name", "email", "phone", "birthdate", "gender", "admin"}


def test_list_users_shape(ana, bob):
    response = ana.client.get("/users")
    assert response.status_code == 200
    assert {u["dni"] for u in response.json()} == {DNI_A, DNI_B}


def test_patch_email_phone_password_pin(ana):
    email = ana.client.patch(ana.url(), {"pin": PIN, "email": "New@Example.com"}, format="json")
    assert (email.status_code, email.json()["email"]) == (200, "new@example.com")

    phone = ana.client.patch(ana.url(), {"pin": PIN, "phone": "+34666777888"}, format="json")
    assert (phone.status_code, phone.json()["phone"]) == (200, "+34666777888")

    password = ana.client.patch(ana.url(), {"pin": PIN, "password": "Other_Pass_9"}, format="json")
    assert password.status_code == 200
    #assert User.objects.get(dni=DNI_A).password == "Other_Pass_9"
    assert User.objects.get(dni=DNI_A).check_password("Other_Pass_9") 

    pin = ana.client.patch(ana.url(), {"pin": PIN, "newPin": "654321"}, format="json")
    assert pin.status_code == 200
    assert User.objects.get(dni=DNI_A).pin == "654321"


def test_patch_errors(ana):
    wrong_pin = ana.client.patch(ana.url(), {"pin": "000000", "email": "a@b.com"}, format="json")
    no_pin = ana.client.patch(ana.url(), {"email": "a@b.com"}, format="json")
    bad_email = ana.client.patch(ana.url(), {"pin": PIN, "email": "nope"}, format="json")
    bad_phone = ana.client.patch(ana.url(), {"pin": PIN, "phone": "+34abc"}, format="json")
    bad_password = ana.client.patch(ana.url(), {"pin": PIN, "password": "weak"}, format="json")
    bad_new_pin = ana.client.patch(ana.url(), {"pin": PIN, "newPin": "12"}, format="json")
    nothing = ana.client.patch(ana.url(), {"pin": PIN}, format="json")
    assert (wrong_pin.status_code, wrong_pin.json()["code"]) == (422, "INVALID_PIN")
    assert (no_pin.status_code, no_pin.json()["code"]) == (400, "INVALID_PIN_FORMAT")
    assert (bad_email.status_code, bad_email.json()["code"]) == (400, "INVALID_EMAIL_FORMAT")
    assert (bad_phone.status_code, bad_phone.json()["code"]) == (400, "INVALID_PHONE_FORMAT")
    assert (bad_password.status_code, bad_password.json()["code"]) == (400, "INVALID_PASSWORD_FORMAT")
    assert (bad_new_pin.status_code, bad_new_pin.json()["code"]) == (400, "INVALID_PIN_FORMAT")
    assert nothing.status_code == 500
    assert set(nothing.json()) == {"error", "message", "timestamp"}


def test_verify_endpoints(ana):
    pin = ana.client.post(ana.url("/security/verify-pin"), {"pin": PIN}, format="json")
    password = ana.client.post(ana.url("/security/verify-password"), {"pin": PIN}, format="json")
    wrong = ana.client.post(ana.url("/security/verify-pin"), {"pin": "000000"}, format="json")
    assert (pin.status_code, pin.json()) == (200, {"pin": PIN})
    #assert (password.status_code, password.json()) == (200, {"password": PASSWORD})
    assert (password.status_code, password.json()) == (200, {"verified": True})
    assert (wrong.status_code, wrong.json()["code"]) == (422, "INVALID_PIN")


def test_delete_user(ana):
    wrong = ana.client.delete(ana.url(), {"pin": "000000"}, format="json")
    assert (wrong.status_code, wrong.json()) == (
        422,
        {"code": "INVALID_PIN", "message": "El PIN és incorrecte!", "metadata": {}},
    )
    user_id = User.objects.get(dni=DNI_A).id
    assert ana.client.delete(ana.url(), {"pin": PIN}, format="json").status_code == 204
    assert not User.objects.filter(dni=DNI_A).exists()
    assert not Session.objects.filter(user_id=user_id).exists()
    assert Account.objects.filter(user_id=user_id).count() == 1

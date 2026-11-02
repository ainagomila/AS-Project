import base64
import json

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client
from oauth2_provider.models import AccessToken, Application

from banking import card_services
from banking.models import Card
from common import crypto
from iam.models import User

from .conftest import DNI_A, DNI_B, PASSWORD, register_payload

pytestmark = pytest.mark.django_db

PAN = "4111111111111111"


def _row(sql, *params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


@pytest.fixture
def card(ana, monkeypatch):
    monkeypatch.setattr(card_services, "verifier_accepts", lambda *args: True)
    body = {"pan": PAN, "expireDate": "05/29", "alias": "A", "cvv": "123", "pin": "1234", "type": "debit", "bank": "B"}
    assert ana.client.post(ana.url(f"/accounts/{ana.iban()}/cards"), body, format="json").status_code == 201
    return Card.objects.get()


def test_personal_data_and_pan_are_not_stored_in_clear(ana, card):
    user_row = _row("SELECT dni_enc, email_enc, phone_number_enc, dni_index, phone_index FROM iam_user")
    card_row = _row("SELECT pan_enc, pin_enc, pan_index FROM banking_card")
    for value in user_row + card_row:
        for secret in (DNI_A, "1234Z", "example.com", "600123456", PAN, "1111"):
            assert secret not in value
    assert all(v.startswith("v1:k1:") for v in user_row[:3] + card_row[:2])
    assert "cvv" not in [c.name for c in connection.introspection.get_table_description(connection.cursor(), "banking_card")]


def test_ciphertext_copied_to_another_row_or_column_does_not_decrypt(ana, bob):
    a, b = User.objects.find_by_dni(DNI_A), User.objects.find_by_dni(DNI_B)
    b.dni_enc = a.dni_enc
    with pytest.raises(InvalidTag):
        b.dni
    a.dni_enc = a.email_enc
    with pytest.raises(InvalidTag):
        a.dni


def test_lookup_by_dni_and_pan_is_normalised(ana, card):
    assert User.objects.find_by_dni(" 12345678z ").pk == User.objects.find_by_dni(DNI_A).pk
    assert Card.objects.find_by_pan("4111 1111 1111 1111").pk == card.pk


def test_dni_differing_only_in_case_is_a_duplicate(client, ana):
    again = client.post("/auth/register", register_payload(dni=DNI_A.lower(), phone="+34611111111"), format="json")
    assert again.status_code == 201  # same answer as a new user (A6), but nothing is created
    assert User.objects.count() == 1


def test_login_form_finds_the_user_by_dni(ana):
    response = Client().post("/accounts/login/", {"username": DNI_A.lower(), "password": PASSWORD})
    assert response.status_code == 302
    wrong = Client().post("/accounts/login/", {"username": DNI_A, "password": "Wrong_123"})
    assert wrong.status_code == 200


def test_rotated_key_encrypts_new_values_and_old_ones_still_decrypt(ana, settings, tmp_path):
    key_file = tmp_path / "keys.json"
    key_file.write_text(json.dumps({"keyBase64": settings.SECURITY_ENCRYPTION_KEY_BASE64}))
    settings.SECURITY_ENCRYPTION_KEY_FILE = str(key_file)
    call_command("generate_key", rotate=True)
    crypto._keyring.cache_clear()
    assert json.loads(key_file.read_text())["current"] == "k2"

    user = User.objects.find_by_dni(DNI_A)
    assert user.email_enc.startswith("v1:k1:") and user.dni == DNI_A
    user.email = "new@example.com"
    user.save()
    assert User.objects.find_by_dni(DNI_A).email_enc.startswith("v1:k2:")
    assert ana.client.get(ana.url()).json()["email"] == "new@example.com"


@pytest.mark.django_db(transaction=True)
def test_migration_encrypts_existing_rows():
    key = crypto._keyring().keys["k1"]
    executor = MigrationExecutor(connection)
    old = [("iam", "0003_hash_user_pin"), ("banking", "0003_remove_card_cvv")]
    executor.migrate(old)
    apps = executor.loader.project_state(old).apps
    apps.get_model("iam", "User").objects.create(
        id="USER-1", dni="12345678Z", email="ana@example.com", name="Ana", phone_prefix="+34",
        phone_number="600123456", birthdate="1995-04-10", gender="female", password="x", pin="x",
    )
    sealed = AESGCM(key).encrypt(b"\0" * 12, b"1234", None)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    apps.get_model("banking", "Card").objects.create(
        id="CARD-1", pan=PAN, expire_date="2029-05-31", alias="A", bank="B", type="DEBIT", status="ACTIVE",
        pin_iv=b64(b"\0" * 12), pin_ciphertext=b64(sealed[:-16]), pin_tag=b64(sealed[-16:]), account_id="ACC-1",
    )

    # A token row referencing the user (deferred foreign key), as on a live database.
    app = Application.objects.create(
        client_id="c", client_type="public", authorization_grant_type="authorization-code", name="c",
    )
    AccessToken.objects.create(
        user_id="USER-1", application=app, token="t", expires="2030-01-01T00:00Z", scope="banking",
    )

    def forward():
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        user, card = User.objects.find_by_dni(DNI_A), Card.objects.find_by_pan(PAN)
        assert (user.dni, user.email, user.phone) == (DNI_A, "ana@example.com", "+34600123456")
        assert (card.pan, card.pin) == (PAN, "1234")
        assert User.objects.phone_exists("+34", "600123456")

    forward()
    executor = MigrationExecutor(connection)
    executor.migrate(old)  # the reverse migration restores the old columns
    apps = executor.loader.project_state(old).apps
    assert apps.get_model("iam", "User").objects.get().email == "ana@example.com"
    assert apps.get_model("banking", "Card").objects.get().pan == PAN
    forward()

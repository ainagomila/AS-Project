from datetime import date

import pytest
from cryptography.exceptions import InvalidTag

from common import crypto
from common import validators as v
from common.errors import STATUS_BY_CODE, AppError


AAD = "iam_user.email_enc.USER-1"


def test_aes_round_trip_uses_fresh_nonce_and_records_the_key_id():
    first, second = crypto.encrypt("Secret_123", AAD), crypto.encrypt("Secret_123", AAD)
    assert first != second
    assert first.startswith("v1:k1:")
    assert crypto.decrypt(first, AAD) == "Secret_123"


def test_aes_rejects_tampered_ciphertext_and_other_cells():
    version, kid, nonce, _ = crypto.encrypt("123456", AAD).split(":")
    other = crypto.encrypt("654321", AAD).split(":")[3]
    with pytest.raises(InvalidTag):
        crypto.decrypt(f"{version}:{kid}:{nonce}:{other}", AAD)
    token = crypto.encrypt("123456", AAD)
    for aad in ["iam_user.email_enc.USER-2", "iam_user.dni_enc.USER-1"]:
        with pytest.raises(InvalidTag):
            crypto.decrypt(token, aad)


def test_blind_index_is_keyed_and_separated_by_purpose():
    index = crypto.blind_index("12345678Z", "iam_user.dni_index")
    assert len(index) == 64 and "12345678" not in index
    assert index == crypto.blind_index("12345678Z", "iam_user.dni_index")
    assert index != crypto.blind_index("12345678Z", "banking_card.pan_index")


@pytest.mark.parametrize("dni", ["12345678Z", " 12345678z ", "X1234567L"])
def test_valid_dni(dni):
    assert v.validate_dni(dni)


@pytest.mark.parametrize("dni", ["12345678A", "1234", "", "A2345678Z"])
def test_invalid_dni(dni):
    with pytest.raises(ValueError):
        v.validate_dni(dni)


def test_email_is_lowercased_and_checked():
    assert v.validate_email(" Ana@Example.COM ") == "ana@example.com"
    for bad in ["", "ana", "ana@x", "a..b@example.com", ".ana@example.com"]:
        with pytest.raises(ValueError):
            v.validate_email(bad)


@pytest.mark.parametrize("password", ["short1!", "nouppercase1!", "NOLOWERCASE1!", "NoDigits!!", "NoSpecial11", " Padded_123"])
def test_weak_passwords_rejected(password):
    with pytest.raises(ValueError):
        v.validate_password(password)


def test_user_pin_is_six_digits():
    assert v.validate_user_pin("123456") == "123456"
    for bad in [None, "12345", "1234567", "12a456"]:
        with pytest.raises(ValueError):
            v.validate_user_pin(bad)


def test_birthdate_formats_and_age():
    assert v.validate_birthdate("1995-04-10") == date(1995, 4, 10)
    assert v.validate_birthdate("10/04/1995") == date(1995, 4, 10)
    for bad in ["", "tomorrow", f"{date.today().year - 5}-01-01", "2999-01-01"]:
        with pytest.raises(ValueError):
            v.validate_birthdate(bad)


def test_phone_rules():
    assert v.validate_phone("+34", "600 123-456") == ("+34", "600123456")
    for prefix, number in [("34", "600123456"), ("+0", "600123456"), ("+34", "123"), ("+34", "0000")]:
        with pytest.raises(ValueError):
            v.validate_phone(prefix, number)


def test_iban_cvv_card_pin_currency_money():
    assert v.is_valid_iban("es91 2100 0418 4502 0005 1332")
    assert not v.is_valid_iban("ES0000000000000000000000")
    assert v.validate_iban("es91 2100 0418 4502 0005 1332") == "ES9121000418450200051332"
    assert v.is_valid_iban(v.random_spanish_iban())
    assert v.validate_cvv("123") == "123"
    assert v.validate_card_pin("1234") == "1234"
    assert v.validate_currency("eur") == "EUR"
    assert str(v.money_amount("10.005")) == "10.01"
    for check, bad in [(v.validate_cvv, "12"), (v.validate_card_pin, "123456"), (v.validate_currency, "JPY")]:
        with pytest.raises(ValueError):
            check(bad)


def test_error_status_mapping():
    assert AppError("USER_NOT_FOUND", "x").status == 404
    assert AppError("USER_ALREADY_EXISTS", "x").status == 409
    assert AppError("INVALID_CREDENTIALS", "x").status == 400
    assert AppError("INVALID_PIN", "x").status == 422
    assert AppError("UNAUTHORIZED", "x").status == 403
    assert AppError("SOMETHING_UNMAPPED", "x").status == 500
    assert "TRICOUNT_NOT_FOUND" not in STATUS_BY_CODE

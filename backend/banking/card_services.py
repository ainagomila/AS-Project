"""Card business rules, ported from CardCommandService and CardQueryService."""

import calendar
import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from django.conf import settings

from common import ids
from common import validators as v
from common.errors import AppError
from common.validators import has_text
from iam.services import find_by_dni

from .models import Account, Card
from .services import find_by_iban, require_active_account

CARD_TYPES = ("DEBIT", "CREDIT")
CARD_STATUSES = ("ACTIVE", "FREEZED", "DEAD")


def card_response(card, iban):
    return {
        "pan": card.pan,
        "iban": iban,
        "alias": card.alias,
        "bank": card.bank,
        "type": card.type,
        "status": card.status,
        "expiryDate": card.expire_date_card_format,
    }


def find_by_pan(pan):
    return Card.objects.find_by_pan(pan)


def parse_expire_date(raw):
    """Epoch millis, yyyy-MM-dd or MM/yy (stored as the last day of the month)."""
    try:
        return datetime.fromtimestamp(int(raw) / 1000, tz=timezone.utc).date()
    except (ValueError, OverflowError, OSError):
        pass
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass
    try:
        month = datetime.strptime(raw, "%m/%y")
    except ValueError:
        raise ValueError(
            "ExpireDate format invalid. Use epoch millis, yyyy-MM-dd or MM/yy. "
            f"Valor rebut: {raw}"
        ) from None
    return date(month.year, month.month, calendar.monthrange(month.year, month.month)[1])


def _require(field, value):
    if not has_text(value):
        raise ValueError(f"El '{field}' de Card ha de tenir un valor diferent a null o blank!")


# ---------------------------------------------------------------- queries

def get_card(dni, pan):
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    card = find_by_pan(pan)
    if card is None:
        raise AppError("CARD_NOT_FOUND", "Targeta inexistent")
    account = Account.objects.filter(id=card.account_id).first()
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Compte inexistent")
    if account.user_id != user.id:
        raise AppError("UNAUTHORIZED", "Targeta no vinculada a l'usuari")
    return card_response(card, account.iban)


def list_account_cards(dni, iban):
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent!")
    account = find_by_iban(iban)
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Account inexistenT!")
    if account.user_id != user.id:
        raise AppError("INTERNAL_ERROR", "Account no pertany a User!")
    cards = Card.objects.filter(account_id=account.id)
    return {"cards": [card_response(c, iban) for c in cards]}


def list_user_cards(dni):
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    cards = []
    for account in Account.objects.filter(user_id=user.id):
        for card in Card.objects.filter(account_id=account.id):
            cards.append(card_response(card, account.iban))
    return {"cards": cards}


# ---------------------------------------------------------------- commands

def _owned_card(user, iban, pan, not_owner_message):
    account = find_by_iban(iban)
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Compte inexistent!")
    if account.user_id != user.id:
        raise AppError("UNAUTHORIZED", not_owner_message)
    card = find_by_pan(pan)
    if card is None:
        raise AppError("CARD_NOT_FOUND", "Targeta inexistent!")
    if card.account_id != account.id:
        raise AppError("UNAUTHORIZED", "La targeta no pertany a aquest compte.")
    return card


def get_owned_card(dni, iban, pan):
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    return _owned_card(user, iban, pan, "El compte no pertany a aquest usuari.")


def get_owned_card_with_pin(dni, iban, pan, pin):
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent!")
    if not has_text(pin):
        raise AppError("INVALID_PIN_FORMAT", "El PIN és obligatori.")
    if not user.check_pin(pin):
        raise AppError("INVALID_PIN", "El PIN és incorrecte!")
    return _owned_card(user, iban, pan, "El compte no pertany a l'usuari.")


def _is_valid(validator, value):
    if not has_text(value):
        return False
    try:
        validator(value)
        return True
    except ValueError:
        return False


def verifier_accepts(pan, expire_date, cvv):
    """Ask the verifier service whether the CVV matches the PAN and expiry date."""
    request = urllib.request.Request(
        f"{settings.VERIFIER_URL}/verify",
        data=json.dumps(
            {"PAN": pan, "CVV": cvv, "expiration_date": expire_date.strftime("%m/%y")}
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response) is True
    except urllib.error.HTTPError as exc:
        if exc.code == 422:  # the verifier rejected the PAN, CVV or date itself
            return False
        raise AppError("INFRA_ERROR", "Servei de verificació no disponible") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise AppError("INFRA_ERROR", "Servei de verificació no disponible") from exc


def add_card(dni, iban, pan, expire_date, alias, cvv, pin, card_type, bank):
    pan = re.sub(r"\s+", "", pan)  # a missing PAN is a 500 in the original too
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    if not has_text(pan):
        raise AppError("INVALID_PAN_FORMAT", "PAN obligatori")
    if find_by_pan(pan) is not None:
        raise AppError("CARD_ALREADY_EXISTS", "Ja existeix una targeta")
    if not _is_valid(v.validate_card_pin, pin):
        raise AppError("INVALID_PIN_FORMAT", "PIN invàlid")
    if not _is_valid(v.validate_cvv, cvv):
        raise AppError("INVALID_CVV_FORMAT", "CVV invàlid")
    if not has_text(bank):
        raise AppError("BANK_NOT_FOUND", "El banc és obligatori")
    if not has_text(iban):
        raise AppError("INVALID_IBAN_FORMAT", "IBAN o compte obligatori")
    if not has_text(card_type) or card_type.upper() not in CARD_TYPES:
        raise AppError("INVALID_TYPE_FORMAT", "Tipus de targeta invàlid")

    account = find_by_iban(iban)
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Compte inexistent ni IBAN")
    if account.user_id != user.id:
        raise AppError("UNAUTHORIZED", "El compte no pertany a l'usuari")
    require_active_account(account)

    # The factory checks are not caught in the original: a blank expiry date or
    # alias, or an unparseable expiry date, answers 500.
    _require("expireDate", expire_date)
    _require("alias", alias)
    expire = parse_expire_date(expire_date)
    cvv = v.validate_cvv(cvv)
    if not verifier_accepts(pan, expire, cvv):
        raise AppError("INVALID_CARD", "Les dades de la targeta no són vàlides")
    card = Card(
        id=ids.generate("CARD"),
        pan=pan,
        expire_date=expire,
        bank=bank,
        alias=alias,
        type=card_type.upper(),
        status="ACTIVE",
        account_id=account.id,
    )
    card.pin = v.validate_card_pin(pin)
    card.save()
    return card_response(card, account.iban)


def delete_card(dni, iban, pan, pin):
    get_owned_card_with_pin(dni, iban, pan, pin).delete()


def update_alias(dni, iban, pan, alias):
    if not has_text(alias):
        raise AppError("APPLICATION_ERROR", "Cal proporcionar el nou alias.")
    card = get_owned_card(dni, iban, pan)
    card.alias = alias
    card.save()
    return card_response(card, iban)


def update_status(dni, iban, pan, status):
    if not has_text(status):
        raise AppError("APPLICATION_ERROR", "Cal proporcionar el nou staus.")
    card = get_owned_card(dni, iban, pan)
    if status not in CARD_STATUSES:
        raise AppError("APPLICATION_ERROR", f"Invalid card status: {status}")
    card.status = status
    card.save()
    return card_response(card, iban)


def verify_card(dni, iban, pan, pin):
    if not has_text(pan):
        raise AppError("INVALID_PAN_FORMAT", "PAN oblogatori per a accedir a la targeta!")
    if not has_text(pin):
        raise AppError("INVALID_PIN_FORMAT", "El PIN és obligatori per a verificar la targeta!")
    card = get_owned_card_with_pin(dni, iban, pan, pin)
    if card.status != "ACTIVE":
        raise AppError("CARD_BLOCKED", "La targeta no està activa")
    # The card PIN and the CVV are never returned.
    return {"pan": card.pan, "expireDate": card.expire_date_card_format}

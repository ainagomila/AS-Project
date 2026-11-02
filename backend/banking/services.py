"""Account business rules, ported from AccountCommandService and
AccountQueryService."""

from decimal import Decimal

from django.db import transaction

from common import ids
from common import validators as v
from common.errors import AppError
from common.validators import has_text
from iam.services import find_by_dni

from .models import Account, Card


def account_response(account):
    return {
        "iban": account.iban,
        "bank": account.bank,
        "name": account.name,
        "balance": float(account.balance),
        "currency": account.currency,
    }


def find_by_iban(iban):
    return Account.objects.filter(iban=iban).first()


def get_owned_account(dni, iban, account_missing="Compte inexistent!"):
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent!")
    return _owned(user, iban, account_missing)


def get_owned_account_with_pin(dni, iban, pin):
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent!")
    if not has_text(pin):
        raise AppError("INVALID_PIN_FORMAT", "El PIN és obligatori!")
    if not user.check_pin(pin):
        raise AppError("INVALID_PIN", "El PIN és incorrecte!")
    return _owned(user, iban, "Compte inexistent!")


def require_active_account(account):
    if account.status != "ACTIVE":
        raise AppError("ACCOUNT_BLOCKED", "El compte no està actiu")


def _owned(user, iban, account_missing):
    account = find_by_iban(iban)
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", account_missing)
    if account.user_id != user.id:
        raise AppError("UNAUTHORIZED", "El compte no pertany a aquest usuari.")
    return account


def get_account(dni, iban):
    return account_response(get_owned_account(dni, iban, "Compte inexistent"))


def list_accounts(dni):
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent!")
    return {"accounts": [account_response(a) for a in Account.objects.filter(user_id=user.id)]}


def add_account(dni, iban, name, bank, currency):
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    if not has_text(name):
        raise AppError("APPLICATION_ERROR", "El nom del compte és obligatori")
    if not has_text(bank):
        raise AppError("BANK_NOT_FOUND", "El banc és obligatori")
    if not v.is_valid_iban(iban):
        raise AppError("INVALID_IBAN_FORMAT", "IBAN invàlid")
    if find_by_iban(iban) is not None:
        raise AppError("ACCOUNT_ALREADY_EXISTS", "El compte ja existeix")

    # Not caught in the original either: a missing or unknown currency is a 500.
    if not has_text(currency):
        raise ValueError("El 'currency' d'Account ha de tenir un valor diferent a null o blank!")
    account = Account.objects.create(
        id=ids.generate("ACC"),
        name=name,
        bank=bank,
        balance=Decimal("0.00"),  # new accounts open empty; a client balance is ignored
        currency=v.validate_currency(currency),
        iban=v.validate_iban(iban),
        user_id=user.id,
    )
    return account_response(account)


def rename_account(dni, iban, name):
    if not has_text(name):
        raise AppError("APPLICATION_ERROR", "Cal proporcionar el nou nom")
    account = get_owned_account(dni, iban)
    account.name = name
    account.save()
    return account_response(account)


def delete_account(dni, iban, pin):
    """Delete the account and its cards. Payments are kept as the counterparty's history."""
    account = get_owned_account_with_pin(dni, iban, pin)
    with transaction.atomic():
        Card.objects.filter(account_id=account.id).delete()
        account.delete()

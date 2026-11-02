from django.utils import timezone

from common.errors import AppError

from .models import ACCOUNT_STATUSES, CARD_STATUSES, Account, Card


def _reason(data):
    reason = str(data.get("reason", "")).strip()
    if not reason or len(reason) > 255:
        raise AppError("INVALID_STATUS_REASON", "El motivo es obligatorio y debe tener como máximo 255 caracteres")
    return reason


def _status(data, allowed):
    status = str(data.get("status", "")).strip().upper()
    if status not in allowed:
        raise AppError("INVALID_STATUS", "Estado de producto no válido")
    return status


def _account_response(account):
    return {
        "id": account.id,
        "iban": f"{account.iban[:4]} **** **** {account.iban[-4:]}",
        "ownerId": account.user_id,
        "name": account.name,
        "bank": account.bank,
        "currency": account.currency,
        "status": account.status,
        "reason": account.status_reason,
        "updatedAt": account.status_updated_at.isoformat() if account.status_updated_at else None,
    }


def _card_response(card):
    account = Account.objects.filter(id=card.account_id).first()
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Compte inexistent")
    return {
        "id": card.id,
        "accountId": card.account_id,
        "iban": f"{account.iban[:4]} **** **** {account.iban[-4:]}",
        "ownerId": account.user_id,
        "last4": card.pan[-4:],
        "alias": card.alias,
        "type": card.type,
        "status": card.status,
        "reason": card.status_reason,
        "updatedAt": card.status_updated_at.isoformat() if card.status_updated_at else None,
    }


def list_accounts():
    return {"accounts": [_account_response(a) for a in Account.objects.order_by("id")]}


def list_cards():
    return {"cards": [_card_response(c) for c in Card.objects.order_by("id")]}


def update_account(account_id, data):
    account = Account.objects.filter(id=account_id).first()
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Compte inexistent")
    account.status = _status(data, ACCOUNT_STATUSES)
    account.status_reason = _reason(data)
    account.status_updated_at = timezone.now()
    account.save(update_fields=["status", "status_reason", "status_updated_at"])
    return _account_response(account)


def update_card(card_id, data):
    card = Card.objects.filter(id=card_id).first()
    if card is None:
        raise AppError("CARD_NOT_FOUND", "Targeta inexistent")
    card.status = _status(data, CARD_STATUSES)
    card.status_reason = _reason(data)
    card.status_updated_at = timezone.now()
    card.save(update_fields=["status", "status_reason", "status_updated_at"])
    return _card_response(card)

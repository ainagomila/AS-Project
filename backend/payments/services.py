"""Transfer business rules, ported from TransferCommandService,
TransfersQueryService and AuxPaymentService."""

import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from django.db.models import Q

from banking.services import find_by_iban
from common import ids
from common import validators as v
from common.errors import AppError
from common.validators import has_text
from iam.services import find_by_dni

from .models import Payment

PAYMENT_CATEGORIES = (
    "FOOD", "RENT", "UTILITIES", "TRANSPORT", "ENTERTAINMENT",
    "SALARY", "FEES", "HEALTH", "EDUCATION", "OTHER",
)  # fmt: skip


def _resolve_user_account(dni, iban, pin=None, with_pin=False):
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "User inexistent!")
    if with_pin:
        if not has_text(pin):
            raise AppError("INVALID_PIN_FORMAT", "El PIN és obligatori!")
        if not user.check_pin(pin):
            raise AppError("INVALID_PIN", "El PIN és incorrecte!")
    account = find_by_iban(iban)
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Account inexitent!")
    if account.user_id != user.id:
        raise AppError("UNAUTHORIZED", "Account no pertany a User!")
    return account


def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def add_transfer(dni, iban, beneficiary, destination_iban, amount, currency, concept, pin,
                 categories):
    if destination_iban is not None:
        destination_iban = re.sub(r"\s+", "", destination_iban)
    source = _resolve_user_account(dni, iban, pin, with_pin=True)

    if not has_text(beneficiary):
        raise AppError("APPLICATION_ERROR", "El camp 'beneficiary' és obligatori!")
    if not v.is_valid_iban(destination_iban):
        raise AppError("INVALID_IBAN_FORMAT", "El 'destinationIban' és invàlid.")
    if amount is None or Decimal(str(amount)) <= 0:
        raise AppError("DOMAIN_ERROR", "L''amount' ha de ser estrictament positiu.")
    if not has_text(currency):
        raise AppError("DOMAIN_ERROR", "La 'currency' és obligatòria.")
    if not has_text(concept):
        raise AppError("APPLICATION_ERROR", "El camp 'concept' és obligatori.")

    parsed_categories = []
    for raw in categories or []:
        if not has_text(raw):
            continue
        category = raw.strip().upper()
        if category not in PAYMENT_CATEGORIES:
            raise AppError("DOMAIN_ERROR", f"Categoria de pagament invalida: '{raw}'")
        if category not in parsed_categories:
            parsed_categories.append(category)

    destination = find_by_iban(destination_iban)
    if destination is None:
        raise AppError("ACCOUNT_NOT_FOUND", "El compte destí és inexistent!")

    # An unknown currency is not caught in the original either and answers 500.
    transfer_amount = v.money_amount(amount)
    transfer_currency = v.validate_currency(currency)
    if source.currency != transfer_currency:
        raise AppError(
            "DOMAIN_ERROR", "La divisa del compte d'origen no coincideix amb la del pagament!"
        )
    if destination.currency != transfer_currency:
        raise AppError(
            "DOMAIN_ERROR", "La divisa del compte destí no coincideix amb la del pagament!"
        )

    if source.balance < transfer_amount:
        raise AppError("INSUFFICIENT_FUNDS", "Fons insuficients al compte d'origen!")
    source.balance = source.balance - transfer_amount
    destination.balance = destination.balance + transfer_amount

    # Three independent writes, in this order, with no transaction: same as the
    # original's three upserts.
    source.save()
    destination.save()
    Payment.objects.create(
        id=ids.generate("PAY"),
        emitter_id=source.iban,
        receiver_id=destination_iban,
        type="BANK_TRANSFER",
        categories=parsed_categories,
        amount=transfer_amount,
        currency=transfer_currency,
        concept=concept,
        payment_date=_now_iso(),
        status="COMPLETED",
        failure_reason=None,
    )


def _payment_date(payment):
    return date.fromisoformat(payment.payment_date[:10])


def _parse_instant(raw):
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _sort(payments, sort):
    spec = (sort or "").lower().strip().replace(", ", ",")
    if spec == "date,asc":
        return sorted(payments, key=_payment_date)
    if spec == "alpha,asc":
        return sorted(payments, key=lambda p: p.concept.lower())
    if spec == "alpha,desc":
        return sorted(payments, key=lambda p: p.concept.lower(), reverse=True)
    return sorted(payments, key=_payment_date, reverse=True)


def transfer_response(payment, iban):
    amount = float(payment.amount)
    return {
        "title": payment.concept,
        "date": payment.payment_date,
        "amount": -amount if iban == payment.emitter_id else amount,
        "currency": payment.currency,
        "categories": payment.categories,
    }


def payments_for_account(iban, q=None, only_expenses=None, date_from=None, date_to=None,
                         sort=None):
    # Unparseable dates are a 500 in the original as well.
    date_from = date.fromisoformat(date_from) if has_text(date_from) else None
    date_to = date.fromisoformat(date_to) if has_text(date_to) else None
    start = datetime.combine(date_from or date(1970, 1, 1), datetime.min.time(), timezone.utc)
    end = (
        datetime.combine(date_to + timedelta(days=1), datetime.min.time(), timezone.utc)
        if date_to
        else datetime.now(timezone.utc)
    )

    payments = [
        p
        for p in Payment.objects.filter(Q(emitter_id=iban) | Q(receiver_id=iban))
        if start <= _parse_instant(p.payment_date) <= end
    ]
    if date_from:
        payments = [p for p in payments if _payment_date(p) >= date_from]
    if date_to:
        payments = [p for p in payments if _payment_date(p) <= date_to]
    if only_expenses:
        payments = [p for p in payments if p.emitter_id == iban]
    if has_text(q):
        needle = q.lower().strip()
        payments = [p for p in payments if needle in p.concept.lower()]
    return {"transfers": [transfer_response(p, iban) for p in _sort(payments, sort)]}


def list_transfers(dni, iban, **filters):
    account = _resolve_user_account(dni, iban)
    return payments_for_account(account.iban, **filters)

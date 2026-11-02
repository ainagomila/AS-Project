"""Administrator business rules.

All mutating operations here write an audit log entry, and role/active changes
are guarded so that an administrator cannot lock themselves out and the system
always keeps at least one active administrator (inventory item X5).
"""

from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from banking.card_services import CARD_STATUSES
from banking.models import ACCOUNT_STATUSES, Account, Card
from banking.services import find_by_iban
from common import ids
from common import validators as v
from common.errors import AppError
from common.validators import has_text
from payments.models import Payment
from payments.services import payments_for_account

from . import services, system_settings
from .models import AuditLog, Role, User


# ---------------------------------------------------------------- audit

def record_audit(actor, action, target_type, target_id="", detail=None):
    return AuditLog.objects.create(
        id=ids.generate("AUD"),
        actor_id=actor.id,
        actor_dni=actor.dni,
        action=action,
        target_type=target_type,
        target_id=target_id or "",
        detail=detail or {},
    )


def audit_log_response(entry):
    return {
        "id": entry.id,
        "actorDni": entry.actor_dni,
        "action": entry.action,
        "targetType": entry.target_type,
        "targetId": entry.target_id,
        "detail": entry.detail,
        "createdAt": entry.created_at.isoformat(),
    }


def list_audit_logs():
    return {"auditLogs": [audit_log_response(e) for e in AuditLog.objects.all()[:500]]}


# ---------------------------------------------------------------- users

def _target_user(dni):
    user = services.find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    return user


def admin_user_response(user):
    account_ids = Account.objects.filter(user_id=user.id).values_list("id", flat=True)
    return {
        **services.user_response(user),
        "active": user.is_active,
        "locked": bool(user.locked_until is not None and user.locked_until > timezone.now()),
        "accountCount": Account.objects.filter(user_id=user.id).count(),
        "cardCount": Card.objects.filter(account_id__in=account_ids).count(),
    }


def list_users():
    return [admin_user_response(u) for u in User.objects.all()]


def create_user(actor, *, name, dni, email, phone, password, birthdate, gender, pin,
                role=Role.USER, active=True):
    required = [
        (dni, "INVALID_DNI_FORMAT", "El DNI és obligatori"),
        (name, "MISSING_FIELDS", "El nom és obligatori"),
        (password, "MISSING_FIELDS", "La contrassenya és obligatòria"),
        (email, "INVALID_EMAIL_FORMAT", "L'email és obligatori"),
        (phone, "INVALID_PHONE_FORMAT", "El telèfon és obligatori"),
        (birthdate, "INVALID_BIRTHDAY_FORMAT", "La data de naixement és obligatòria"),
        (gender, "MISSING_FIELDS", "El gènere és obligatori"),
        (pin, "INVALID_PIN_FORMAT", "El PIN és obligatori"),
    ]
    for value, code, message in required:
        if not has_text(value):
            raise AppError(code, message)

    if role not in Role.values:
        raise AppError("INVALID_ROLE", "Rol invàlid")
    if not isinstance(active, bool):
        raise AppError("MISSING_FIELDS", "Cal informar 'active' (true o false)")

    user = services.create_user_record(name, dni, email, phone, password, birthdate, gender, pin)
    user.role = role
    user.is_active = active
    user.save()
    services._initial_account(user)

    record_audit(actor, "user.create", "user", user.dni, {"role": role, "active": active})
    return admin_user_response(user)


def _guard_admin_removal(actor, target, new_role, new_active):
    if actor.id == target.id:
        raise AppError("CANNOT_MODIFY_SELF", "No pots modificar el teu propi compte")
    was_active_admin = target.role == Role.ADMIN and target.is_active
    will_be_active_admin = new_role == Role.ADMIN and new_active
    if was_active_admin and not will_be_active_admin:
        if User.objects.filter(role=Role.ADMIN, is_active=True).count() <= 1:
            raise AppError("LAST_ADMIN", "No es pot treure l'últim administrador actiu")


def update_user(actor, dni, data):
    target = _target_user(dni)
    has_role = "role" in data
    has_active = "active" in data
    if not has_role and not has_active:
        raise AppError("MISSING_FIELDS", "Cal informar 'active' o 'role'")

    new_role = data.get("role", target.role)
    new_active = data.get("active", target.is_active)
    if has_role and new_role not in Role.values:
        raise AppError("INVALID_ROLE", "Rol invàlid")
    if has_active and not isinstance(new_active, bool):
        raise AppError("MISSING_FIELDS", "Cal informar 'active' (true o false)")

    _guard_admin_removal(actor, target, new_role, new_active)

    changes = []
    update_fields = []
    if has_role and new_role != target.role:
        changes.append(f"role {target.role} -> {new_role}")
        target.role = new_role
        update_fields.append("role")
    if has_active and new_active != target.is_active:
        changes.append(f"active {target.is_active} -> {new_active}")
        target.is_active = new_active
        update_fields.append("is_active")

    if update_fields:
        target.save(update_fields=update_fields)
        record_audit(actor, "user.update", "user", target.dni, {"changes": changes})
    return admin_user_response(target)


def delete_user(actor, dni):
    target = _target_user(dni)
    _guard_admin_removal(actor, target, Role.USER, False)

    accounts = Account.objects.filter(user_id=target.id)
    ibans = list(accounts.values_list("iban", flat=True))
    account_ids = list(accounts.values_list("id", flat=True))

    Card.objects.filter(account_id__in=account_ids).delete()
    if ibans:
        Payment.objects.filter(Q(emitter_id__in=ibans) | Q(receiver_id__in=ibans)).delete()
    accounts.delete()
    target.delete()  # sessions cascade through the FK

    record_audit(actor, "user.delete", "user", dni, {"accounts": len(ibans)})


def reset_user_password(actor, dni, new_password):
    target = _target_user(dni)
    if not has_text(new_password):
        raise AppError("INVALID_PASSWORD_FORMAT", "La nova contrassenya és obligatòria")
    try:
        target.password = v.validate_password(new_password)
    except ValueError as exc:
        raise AppError("INVALID_PASSWORD_FORMAT", str(exc)) from None
    target.save()

    # Revoke every live session and clear any lockout after an admin reset.
    target.sessions.all().delete()
    target.failed_login_attempts = 0
    target.locked_until = None
    target.save(update_fields=["failed_login_attempts", "locked_until"])

    record_audit(actor, "user.reset_password", "user", target.dni)
    return admin_user_response(target)


# ---------------------------------------------------------------- accounts

def _owner_label(user_id):
    owner = User.objects.filter(id=user_id).first()
    return {"dni": owner.dni if owner else None, "name": owner.name if owner else None}


def admin_account_response(account):
    return {
        "iban": account.iban,
        "name": account.name,
        "bank": account.bank,
        "balance": float(account.balance),
        "currency": account.currency,
        "status": account.status,
        "owner": _owner_label(account.user_id),
    }


def list_user_accounts(dni):
    user = _target_user(dni)
    accounts = Account.objects.filter(user_id=user.id)
    return {"accounts": [admin_account_response(a) for a in accounts]}


def list_all_accounts():
    return {"accounts": [admin_account_response(a) for a in Account.objects.all()]}


def set_account_status(actor, iban, status):
    account = find_by_iban(iban)
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Compte inexistent")
    status = (status or "").upper()
    if status not in ACCOUNT_STATUSES:
        raise AppError("APPLICATION_ERROR", f"Invalid account status: {status}")
    if account.status != status:
        account.status = status
        account.save(update_fields=["status"])
        record_audit(actor, "account.status", "account", account.iban, {"status": status})
    return admin_account_response(account)


# ---------------------------------------------------------------- cards

def admin_card_response(card):
    account = Account.objects.filter(id=card.account_id).first()
    return {
        "pan": card.pan,
        "iban": account.iban if account else None,
        "alias": card.alias,
        "bank": card.bank,
        "type": card.type,
        "status": card.status,
        "expiryDate": card.expire_date_card_format,
        "owner": _owner_label(account.user_id) if account else {"dni": None, "name": None},
    }


def list_user_cards(dni):
    user = _target_user(dni)
    account_ids = Account.objects.filter(user_id=user.id).values_list("id", flat=True)
    cards = Card.objects.filter(account_id__in=account_ids)
    return {"cards": [admin_card_response(c) for c in cards]}


def list_all_cards():
    return {"cards": [admin_card_response(c) for c in Card.objects.all()]}


def set_card_status(actor, pan, status):
    card = Card.objects.filter(pan=pan).first()
    if card is None:
        raise AppError("CARD_NOT_FOUND", "Targeta inexistent")
    status = (status or "").upper()
    if status not in CARD_STATUSES:
        raise AppError("APPLICATION_ERROR", f"Invalid card status: {status}")
    if card.status != status:
        card.status = status
        card.save(update_fields=["status"])
        record_audit(actor, "card.status", "card", card.pan, {"status": status})
    return admin_card_response(card)


def delete_card(actor, pan):
    card = Card.objects.filter(pan=pan).first()
    if card is None:
        raise AppError("CARD_NOT_FOUND", "Targeta inexistent")
    card.delete()
    record_audit(actor, "card.delete", "card", pan)


# ---------------------------------------------------------------- transfers

def list_account_transfers(dni, iban):
    user = _target_user(dni)
    account = find_by_iban(iban)
    if account is None or account.user_id != user.id:
        raise AppError("ACCOUNT_NOT_FOUND", "Compte inexistent")
    return payments_for_account(account.iban)


def admin_transfer_response(payment):
    return {
        "id": payment.id,
        "emitter": payment.emitter_id,
        "receiver": payment.receiver_id,
        "type": payment.type,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "concept": payment.concept,
        "categories": payment.categories,
        "date": payment.payment_date,
        "status": payment.status,
    }


def list_all_transfers():
    payments = Payment.objects.all().order_by("-payment_date")
    return {"transfers": [admin_transfer_response(p) for p in payments[:500]]}


# ---------------------------------------------------------------- settings

def list_settings():
    merged = system_settings.all_settings()
    return {
        "settings": [
            {"key": k, "value": v, "description": system_settings.DESCRIPTIONS.get(k, "")}
            for k, v in merged.items()
        ]
    }


def _coerce_setting(key, value):
    if key in ("SESSION_TTL_SECONDS", "LOGIN_MAX_ATTEMPTS", "LOGIN_LOCKOUT_SECONDS"):
        if not isinstance(value, int) or value <= 0:
            raise AppError("APPLICATION_ERROR", f"El valor de {key} ha de ser un enter positiu")
        return value
    if key in ("REGISTRATION_ENABLED", "MAINTENANCE_MODE"):
        if not isinstance(value, bool):
            raise AppError("APPLICATION_ERROR", f"El valor de {key} ha de ser booleà")
        return value
    if key == "TRANSFER_MAX_AMOUNT":
        if value is None:
            return None
        try:
            amount = Decimal(str(value))
        except Exception:
            raise AppError("APPLICATION_ERROR", "TRANSFER_MAX_AMOUNT ha de ser un número o null") from None
        if amount <= 0:
            raise AppError("APPLICATION_ERROR", "TRANSFER_MAX_AMOUNT ha de ser positiu")
        return float(amount)
    return value


def update_setting(actor, key, value):
    if key not in system_settings.DEFAULTS:
        raise AppError("SETTING_NOT_FOUND", "Paràmetre de configuració inexistent")
    normalized = _coerce_setting(key, value)
    system_settings.set_setting(key, normalized)
    record_audit(actor, "setting.update", "setting", key, {"value": normalized})
    return {"key": key, "value": normalized, "description": system_settings.DESCRIPTIONS.get(key, "")}


# ---------------------------------------------------------------- stats

def stats():
    total = Account.objects.aggregate(total=Sum("balance"))["total"] or Decimal("0")
    return {
        "users": User.objects.count(),
        "activeUsers": User.objects.filter(is_active=True).count(),
        "admins": User.objects.filter(role=Role.ADMIN).count(),
        "auditors": User.objects.filter(role=Role.AUDITOR).count(),
        "accounts": Account.objects.count(),
        "cards": Card.objects.count(),
        "transfers": Payment.objects.count(),
        "totalBalance": float(total),
    }

"""Identity-management operations for the protected administration API."""

from django.db import transaction

from banking.models import Account, Card
from common import validators as v
from common.errors import AppError
from common.validators import has_text

from . import services
from .models import CUSTOMER, User


def _target(user_id):
    user = User.objects.filter(id=user_id).first()
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    return user


def response(user):
    return {
        "id": user.id,
        "dni": user.dni,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "active": user.is_active,
    }


def create_user(data):
    required = ("name", "dni", "email", "phone", "password", "birthdate", "gender", "pin")
    if any(not has_text(data.get(field)) for field in required):
        raise AppError("MISSING_FIELDS", "Cal informar tots els camps obligatoris")
    active = data.get("active", True)
    if "role" in data:
        raise AppError("FORBIDDEN", "Els rols de personal només es poden aprovisionar fora de l'API")
    if not isinstance(active, bool):
        raise AppError("MISSING_FIELDS", "Cal informar 'active' (true o false)")

    with transaction.atomic():
        user = services.create_user_record(
            data["name"],
            data["dni"],
            data["email"],
            data["phone"],
            data["password"],
            data["birthdate"],
            data["gender"],
            data["pin"],
        )
        user.role = CUSTOMER
        user.is_active = active
        user.save()
        services.create_initial_account(user)
    return response(user)


def update_user(actor, user_id, data):
    target = _target(user_id)
    if target.id == actor.id:
        raise AppError("FORBIDDEN", "No pots modificar el teu propi compte")
    if target.role != CUSTOMER:
        raise AppError("FORBIDDEN", "Només es poden modificar clients")
    has_active = "active" in data
    if "role" in data:
        raise AppError("FORBIDDEN", "Els rols de personal només es poden aprovisionar fora de l'API")
    if not has_active:
        raise AppError("MISSING_FIELDS", "Cal informar 'active'")
    if has_active and not isinstance(data["active"], bool):
        raise AppError("MISSING_FIELDS", "Cal informar 'active' (true o false)")
    target.is_active = data.get("active", target.is_active)
    target.save(update_fields=["is_active"])
    if has_active and not target.is_active:
        services.revoke_tokens(target)
    return response(target)


def reset_password(actor, user_id, new_password):
    target = _target(user_id)
    if target.id == actor.id or target.role != CUSTOMER:
        raise AppError("FORBIDDEN", "Només es poden modificar clients")
    if not has_text(new_password):
        raise AppError("INVALID_PASSWORD_FORMAT", "La contrasenya és obligatòria")
    try:
        target.set_password(v.validate_password(new_password))
    except ValueError as exc:
        raise AppError("INVALID_PASSWORD_FORMAT", str(exc)) from None
    target.save(update_fields=["password"])
    services.revoke_tokens(target)
    return response(target)


def delete_user(actor, user_id):
    target = _target(user_id)
    if target.id == actor.id or target.role != CUSTOMER:
        raise AppError("FORBIDDEN", "Només es poden eliminar clients")
    with transaction.atomic():
        account_ids = list(Account.objects.filter(user_id=target.id).values_list("id", flat=True))
        Card.objects.filter(account_id__in=account_ids).delete()
        Account.objects.filter(id__in=account_ids).delete()
        services.revoke_tokens(target)
        target.delete()

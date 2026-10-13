"""Auth and user business rules, ported from AuthCommandService,
UserCommandService and UserQueryService."""

import re
import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from banking.models import Account
from common import ids
from common import validators as v
from common.errors import AppError
from common.validators import has_text

from .models import Session, User


# ---------------------------------------------------------------- helpers

def find_by_dni(dni):
    return User.objects.filter(dni=dni).first()


def user_response(user):
    return {
        "dni": user.dni,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "birthdate": user.birthdate.isoformat(),
        "gender": user.gender,
        "admin": user.is_admin,
    }


def _open_session(user):
    user.purge_expired_sessions()
    return Session.objects.create(
        token=str(uuid.uuid4()),
        user=user,
        expires_at=timezone.now() + timedelta(seconds=settings.SESSION_TTL_SECONDS),
    )


def _split_phone(mobile):
    cleaned = re.sub(r"[\s()-]", "", mobile)
    if not cleaned.startswith("+"):
        raise ValueError("El telèfon ha de començar amb + i prefix")
    index = 1
    # Same loop as the original: takes up to three digits after '+'.
    while index <= 3 and index < len(cleaned) and cleaned[index].isdigit():
        index += 1
    if index >= len(cleaned):
        raise ValueError("El número de telèfon és incomplet")
    return cleaned[:index], cleaned[index:]


def _map_domain_error(exc):
    message = str(exc) or "Error de domini"
    if "dni" in message:
        return AppError("INVALID_DNI_FORMAT", message)
    if "email" in message:
        return AppError("INVALID_EMAIL_FORMAT", message)
    if "phone" in message:
        return AppError("INVALID_PHONE_FORMAT", message)
    if "password" in message:
        return AppError("INVALID_PASSWORD_FORMAT", message)
    return AppError("DOMAIN_ERROR", message)


def _require_pin(dni, pin):
    """checkPin + the INVALID_PIN branch every caller repeats in the original."""
    if not has_text(pin):
        raise AppError("INVALID_PIN_FORMAT", "El PIN és obligatori")
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "L'usuari no existeix")
    if user.pin != pin:
        raise AppError("INVALID_PIN", "El PIN és incorrecte!")
    return user


def _user_with_pin(dni, pin):
    if find_by_dni(dni) is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    return _require_pin(dni, pin)


# ---------------------------------------------------------------- auth

def register(name, dni, email, phone, password, birthdate, gender, pin):
    required = [
        (dni, "INVALID_DNI_FORMAT", "El DNI és obligatori"),
        (name, "MISSING_FIELDS", "El nom és obligatori"),
        (password, "MISSING_FIELDS", "La contrassenya és obligatòria al registre"),
        (email, "INVALID_EMAIL_FORMAT", "L'email és obligatori"),
        (phone, "INVALID_PHONE_FORMAT", "El telèfon és obligatori"),
        (birthdate, "INVALID_BIRTHDAY_FORMAT", "La data de naixement és obligatòria"),
        (gender, "MISSING_FIELDS", "El gènere és obligatori"),
        (pin, "INVALID_PIN_FORMAT", "El PIN és obligatori al registre"),
    ]
    for value, code, message in required:
        if not has_text(value):
            raise AppError(code, message)

    if find_by_dni(dni) is not None:
        raise AppError("USER_ALREADY_EXISTS", "Ja existeix un usuari amb el DNI indicat")

    try:
        prefix, number = _split_phone(phone)
        prefix, number = v.validate_phone(prefix, number)
    except ValueError as exc:
        raise AppError("INVALID_PHONE_FORMAT", str(exc)) from None
    if User.objects.filter(phone_prefix=prefix, phone_number=number).exists():
        raise AppError("USER_ALREADY_EXISTS", "Ja existeix un usuari amb el telèfon indicat")

    try:
        user = User(id=ids.generate("USER"), name=name)
        user.password = v.validate_password(password)
        user.pin = v.validate_user_pin(pin)
        user.dni = v.validate_dni(dni)
        user.phone_prefix, user.phone_number = prefix, number
        user.email = v.validate_email(email)
        user.birthdate = v.validate_birthdate(birthdate)
        user.gender = v.validate_gender(gender)
    except ValueError as exc:
        raise _map_domain_error(exc) from None

    user.save()
    session = _open_session(user)

    # Initial "Kofre" account. The original names the factory method
    # createWithZeroBalance but opens the account with 100.
    Account.objects.create(
        id=ids.generate("ACC"),
        name="Kofre",
        bank="Kofre Bank",
        balance=v.money_amount(100),
        currency="EUR",
        iban=v.random_spanish_iban(),
        user_id=user.id,
    )
    return {"message": "User registered successfully", "token": session.token}


def login(dni, password):
    if not has_text(dni) or not has_text(password):
        raise AppError("INVALID_CREDENTIALS", "Credencials invàlides o incompletes")
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    if user.password != password:
        raise AppError("INVALID_CREDENTIALS", "Credencials invàlides")
    if not user.is_active:
        raise AppError("USER_DISABLED", "L'usuari està deshabilitat")
    session = _open_session(user)
    return {"token": session.token, "user": user_response(user)}


def _validate_session_data(dni, token):
    if dni is None and token is None:
        raise AppError("MISSING_FIELDS", "Cal informar la sessió")
    if not has_text(dni):
        raise AppError("INVALID_DNI_FORMAT", "El DNI és obligatori")
    if not has_text(token):
        raise AppError("UNAUTHORIZED", "Token de sessió obligatori")


def logout(dni, token):
    _validate_session_data(dni, token)
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    if not user.check_session(token):
        raise AppError("UNAUTHORIZED", "La sessió no és vàlida")
    user.sessions.filter(token=token).delete()


def find_by_session_token(token):
    session = (
        Session.objects.filter(token=token, expires_at__gte=timezone.now())
        .select_related("user")
        .first()
    )
    return session.user if session else None


def validate(dni, token):
    """Return the session's user or raise. Also used by the authentication class."""
    if not has_text(dni):
        if not has_text(token):
            raise AppError("UNAUTHORIZED", "Token de sessió obligatori")
        user = find_by_session_token(token)
        if user is None:
            raise AppError("UNAUTHORIZED", "Sessió no vàlida")
        return user
    _validate_session_data(dni, token)
    user = find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    if not user.check_session(token):
        raise AppError("UNAUTHORIZED", "Sessió expirada o inexistent")
    return user


def exists(dni):
    if not has_text(dni) or find_by_dni(dni.strip()) is None:
        raise AppError("USER_NOT_FOUND", "L'usuari no existeix al sistema")


# ---------------------------------------------------------------- users

def get_user(dni):
    user = find_by_dni(dni.strip()) if has_text(dni) else None
    if user is None:
        raise AppError("USER_NOT_FOUND", "No s'ha trobat cap usuari amb el DNI especificat")
    return user_response(user)


def list_users():
    return [user_response(u) for u in User.objects.all()]


def update_email(dni, pin, email):
    user = _user_with_pin(dni, pin)
    if not has_text(email):
        raise AppError("APPLICATION_ERROR", "Cal informar 'Email' per actualitzar.")
    if email != user.email:
        try:
            user.email = v.validate_email(email)
        except ValueError as exc:
            raise AppError("INVALID_EMAIL_FORMAT", str(exc)) from None
    user.save()
    return user_response(user)


def split_update_phone(phone):
    """Prefix/number split of the original UpdatePhoneRequest."""
    if " " in phone.strip():
        prefix, rest = re.split(r"\s+", phone.strip(), maxsplit=1)
        return prefix, re.sub(r"\s+", "", rest)
    raw = re.sub(r"\s+", "", phone)
    if len(raw) > 3:
        return raw[:3], raw[3:]
    return raw, ""


def update_phone(dni, pin, prefix, number):
    user = _user_with_pin(dni, pin)
    if not has_text(prefix) or not has_text(number):
        raise AppError("APPLICATION_ERROR", "Cal informar 'prefix' i 'number' per actualitzar.")
    if (prefix, number) != (user.phone_prefix, user.phone_number):
        try:
            user.phone_prefix, user.phone_number = v.validate_phone(prefix, number)
        except ValueError as exc:
            raise AppError("INVALID_PHONE_FORMAT", str(exc)) from None
    user.save()
    return user_response(user)


def update_password(dni, pin, password):
    user = _user_with_pin(dni, pin)
    if not has_text(password):
        raise AppError("APPLICATION_ERROR", "Cal informar 'password' per actualitzar.")
    if user.password != password:
        try:
            user.password = v.validate_password(password)
        except ValueError as exc:
            raise AppError("INVALID_PASSWORD_FORMAT", str(exc)) from None
    user.save()
    return user_response(user)


def update_pin(dni, pin, new_pin):
    user = _user_with_pin(dni, pin)
    if not has_text(new_pin):
        raise AppError("APPLICATION_ERROR", "Cal informar 'pin' per actualitzar.")
    if new_pin != user.pin:
        try:
            user.pin = v.validate_user_pin(new_pin)
        except ValueError as exc:
            raise AppError("INVALID_PIN_FORMAT", str(exc)) from None
    user.save()
    return user_response(user)


def delete_user(dni, pin):
    # Only the user (and their sessions) is removed. Accounts, cards and
    # payments are left behind, as in the original.
    _require_pin(dni, pin).delete()


def verify_pin(dni, pin):
    return {"pin": _user_with_pin(dni, pin).pin}


def verify_password(dni, pin):
    return {"password": _user_with_pin(dni, pin).password}

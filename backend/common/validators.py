"""Validation rules ported from the original value objects.

Each function returns the normalised value or raises ValueError with the
original message. Services decide which error code a failure maps to, exactly
as the original services did with IllegalArgumentException.
"""

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from schwifty import IBAN

DNI_CONTROL = "TRWAGMYFPDXBNJZSQVHLCKE"
EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}$", re.IGNORECASE)
CURRENCIES = ("EUR", "USD", "GBP")
GENDERS = ("MALE", "FEMALE", "OTHER")
ADULT_AGE = 18


def has_text(value):
    """Spring's StringUtils.hasText."""
    return isinstance(value, str) and value.strip() != ""


def as_text(value):
    """Mimic Jackson's coercion of JSON scalars into String fields."""
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _dni_control(digits, letter):
    if DNI_CONTROL[int(digits) % 23] != letter:
        raise ValueError("El 'dni' és incorrecte (lletra de control invàlida)!")


def validate_dni(value):
    norm = re.sub(r"\s+", "", value.strip()).upper()
    if not norm:
        raise ValueError("El 'dni' de User no pot ser blank!")
    if re.fullmatch(r"\d{8}[A-Z]", norm):
        _dni_control(norm[:8], norm[8])
        return norm
    if re.fullmatch(r"[XYZ]\d{7}[A-Z]", norm):
        mapped = {"X": "0", "Y": "1", "Z": "2"}[norm[0]] + norm[1:8]
        _dni_control(mapped, norm[8])
        return value  # the original returns the NIE as received
    raise ValueError("El 'dni' és incorrecte (format invàlid)!")


def validate_email(value):
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("El 'email' de User no pot ser blank!")
    if trimmed.startswith(".") or trimmed.endswith("."):
        raise ValueError("El 'email' és incorrecte (inicia o finalitza amb '.')!")
    if ".." in trimmed:
        raise ValueError("El 'email' és incorrecte (doble punts)!")
    if not EMAIL_PATTERN.fullmatch(trimmed):
        raise ValueError("El 'email' és incorrecte (format invàlid)!")
    return trimmed.lower()


def validate_password(value):
    if len(value) < 8 or len(value) > 128:
        raise ValueError("El 'password' és incorrecte (mida invàlida)!")
    if value != value.strip():
        raise ValueError("El 'password' és incorrecte (no pot començar/acabar en espais)!")
    if not re.search(r"[a-z]", value):
        raise ValueError("El 'password' és incorrecte (ha de contenir mínim una minúscula)!")
    if not re.search(r"[A-Z]", value):
        raise ValueError("El 'password' és incorrecte (ha de contenir mínim una majúscula)!")
    if not re.search(r"\d", value):
        raise ValueError("El 'password' és incorrecte (ha de contenir mínim un dígit)!")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError(
            "El 'password' és incorrecte (ha de contenir mínim un caràcter especial)!"
        )
    return value


def validate_user_pin(value):
    if value is None or not re.fullmatch(r"\d{6}", value):
        raise ValueError("El 'pin' ha de ser un codi de 6 dígits!")
    return value


def validate_birthdate(value):
    raw = value.strip()
    if not raw:
        raise ValueError("El 'birthdate' no pot ser blank!")
    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        try:
            parsed = datetime.strptime(raw, "%d/%m/%Y").date()
        except ValueError:
            raise ValueError("El 'birthdate' és incorrecte (format invàlid)!") from None
    today = date.today()
    if parsed > today:
        raise ValueError("El 'birthdate' és incorrecte (data al futur)!")
    years = today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day))
    if years < ADULT_AGE:
        raise ValueError(f"L'usuari ha de ser major d'edat (>= {ADULT_AGE})!")
    return parsed


def validate_gender(value):
    if not value.strip():
        raise ValueError("El 'gender' no pot ser blank!")
    normalized = value.strip().upper()
    if normalized not in GENDERS:
        raise ValueError("El 'gender' ha de ser MALE, FEMALE o OTHER")
    return normalized


def validate_phone(prefix, number):
    """Return (prefix, number) normalised as the original PhoneNumber does."""
    trimmed = prefix.strip()
    if not trimmed.startswith("+"):
        raise ValueError("El 'prefix' és incorrecte (ha de començar amb +)!")
    if not re.fullmatch(r"[1-9]\d{0,2}", trimmed[1:]):
        raise ValueError("El 'prefix' es incorrecte (format incorrecte)!")
    compact = re.sub(r"[\s\-().]", "", number)
    if not re.fullmatch(r"\d{4,14}", compact):
        raise ValueError("El 'number' és incorrecte (número invàlid)!")
    if set(compact) == {"0"}:
        raise ValueError("El 'number' és incorrecte (no pot ser tot zeros)!")
    if len(trimmed) - 1 + len(compact) > 15:
        raise ValueError("La longitud de 'phoneNumber' és incorrecte (>15 dígits)!")
    return trimmed, compact


def normalize_iban(value):
    return re.sub(r"\s+", "", value).upper()


def is_valid_iban(value):
    if not has_text(value):
        return False
    try:
        IBAN(normalize_iban(value))
        return True
    except ValueError:
        return False


def validate_iban(value):
    normalized = normalize_iban(value)
    try:
        IBAN(normalized)
    except ValueError as exc:
        raise ValueError(f"IBAN invàlid: {exc}") from None
    return normalized


def random_spanish_iban():
    return str(IBAN.random(country_code="ES"))


def validate_cvv(value):
    normalized = re.sub(r"\s+", "", value)
    if not re.fullmatch(r"\d{3,4}", normalized):
        raise ValueError(
            f"CVV invàlid: ha de contenir 3 o 4 dígits numèrics (rebut: {normalized})"
        )
    return normalized


def validate_card_pin(value):
    if not re.fullmatch(r"\d{4}", value):
        raise ValueError(
            f"PIN invàlid: ha de contenir exactament 4 dígits numèrics (rebut: {value})"
        )
    return value


def validate_currency(value):
    for currency in CURRENCIES:
        if currency == str(value).upper():
            return currency
    raise ValueError(f"Invalid currency: {value}")


def money_amount(value):
    """Money's amount normalisation: two decimals, half-up."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

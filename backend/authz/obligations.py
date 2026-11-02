"""Obligation handlers. The enforcement point must fulfil every obligation of a
decision; an obligation it does not know makes it deny the request."""

import re

AUDIT = "urn:kofre:obligation:audit"
MASK = "urn:kofre:obligation:mask-personal-data"
MASK_FIELD = "urn:kofre:obligation:field"

KNOWN = {AUDIT, MASK}


def _mask_dni(value):
    return "*" * max(len(value) - 4, 0) + value[-4:]


def _mask_name(value):
    return " ".join(part[0] + "." for part in value.split() if part)


def _mask_email(value):
    local, _, domain = value.partition("@")
    return (local[:1] + "***@" + domain) if domain else "***"


def _mask_phone(value):
    digits = re.sub(r"\s", "", value)
    return digits[:3] + " *** *** " + digits[-3:] if len(digits) > 6 else "***"


def _mask_iban(value):
    compact = re.sub(r"\s", "", value)
    return compact[:4] + " **** **** " + compact[-4:] if len(compact) > 8 else "****"


MASKERS = {
    "dni": _mask_dni,
    "name": _mask_name,
    "email": _mask_email,
    "phone": _mask_phone,
    "iban": _mask_iban,
}


class UnfulfillableObligation(Exception):
    pass


def check_supported(obligations):
    for obligation in obligations:
        if obligation["id"] not in KNOWN:
            raise UnfulfillableObligation(obligation["id"])
        if obligation["id"] == MASK:
            for name in obligation["attributes"].get(MASK_FIELD, []):
                if name not in MASKERS:
                    raise UnfulfillableObligation(f"{MASK}: no masker for field {name!r}")


def mask(data, fields):
    """Mask the given keys anywhere in a JSON-like structure."""
    if isinstance(data, list):
        return [mask(item, fields) for item in data]
    if isinstance(data, dict):
        return {
            key: (MASKERS[key](value) if key in fields and isinstance(value, str) else mask(value, fields))
            for key, value in data.items()
        }
    return data


def fields_to_mask(obligations):
    return {
        name
        for obligation in obligations
        if obligation["id"] == MASK
        for name in obligation["attributes"].get(MASK_FIELD, [])
    }

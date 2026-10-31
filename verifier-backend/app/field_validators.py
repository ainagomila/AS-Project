import re
from datetime import date

PAN_RE = re.compile(r"[0-9]{13,19}")
CVV_RE = re.compile(r"[0-9]{3}")
DATE_RE = re.compile(r"(0[1-9]|1[0-2])/([0-9]{2})")


def is_luhn_valid(card_number: str) -> bool:
    digits = [int(d) for d in reversed(card_number)]
    total = sum(digits[0::2]) + sum(sum(divmod(d * 2, 10)) for d in digits[1::2])
    return total % 10 == 0


def is_valid_PAN(value: str) -> str:
    if PAN_RE.fullmatch(value) and is_luhn_valid(value):
        return value
    raise ValueError("Invalid PAN")


def is_valid_CVV(value: str) -> str:
    if CVV_RE.fullmatch(value):
        return value
    raise ValueError("Invalid CVV")


def is_valid_date(value: str) -> str:
    """Accepts MM/YY; the card is valid through the end of that month."""
    match = DATE_RE.fullmatch(value)
    if match is None:
        raise ValueError("Invalid expiration date")
    month, year = int(match[1]), 2000 + int(match[2])
    today = date.today()
    if (year, month) < (today.year, today.month):
        raise ValueError("Card expired")
    return value

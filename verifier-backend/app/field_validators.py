import re


def luhn_checksum(card_number: int) -> int:
    def digits_of(n: int) -> list[int]:
        return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = 0
    checksum += sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d*2))
    return checksum % 10

def is_luhn_valid(card_number: int) -> bool:
    return luhn_checksum(card_number) == 0

def is_valid_PAN(value: str) -> bool:
    is_valid_length = len(value) >= 13 and len(value) <= 18
    return is_valid_length and value.isdigit() and is_luhn_valid(int(value))

def is_valid_CVV(value: str) -> bool:
    return len(value) == 3 and value.isdigit()

def is_valid_date(value: str) -> bool:
    MM_YY = re.compile(r'(0[1-9]|1[0-2])/[0-9]{2}')
    return MM_YY.fullmatch(value) is not None

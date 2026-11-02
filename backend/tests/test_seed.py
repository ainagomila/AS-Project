import re
from datetime import date, timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from banking.models import Account, Card
from iam.models import CUSTOMER, User
from iam.management.commands.seed_users import SEED_CARD_PANS, SEED_USERS

pytestmark = pytest.mark.django_db

CUSTOMER_DNIS = [dni for _, dni, _, _, _, role in SEED_USERS if role == CUSTOMER]


def _cards_of(user):
    account_ids = [a.id for a in Account.objects.filter(user_id=user.id)]
    return list(Card.objects.filter(account_id__in=account_ids))


def test_seed_users_creates_each_role_with_an_account():
    call_command("seed_users", password="Seed_Pass1!", pin="654321")

    for _, dni, _, _, _, role in SEED_USERS:
        user = User.objects.find_by_dni(dni)
        assert user.role == role
        assert user.check_password("Seed_Pass1!")
        assert user.check_pin("654321")
        assert Account.objects.filter(user_id=user.id).count() == 1


def test_seed_users_is_idempotent_and_generates_credentials(capsys):
    call_command("seed_users")
    first = User.objects.find_by_dni(SEED_USERS[0][1]).password
    call_command("seed_users", password="Other_Pass1!")

    assert User.objects.count() == len(SEED_USERS)
    assert User.objects.find_by_dni(SEED_USERS[0][1]).password == first
    assert "Password: Kf" in capsys.readouterr().out


def test_customers_get_one_debit_card_with_the_seed_pan():
    call_command("seed_users", password="Seed_Pass1!", pin="654321", card_pin="4321")

    for _, dni, _, _, _, role in SEED_USERS:
        user = User.objects.find_by_dni(dni)
        cards = _cards_of(user)
        if role != CUSTOMER:
            assert cards == []
            continue
        assert len(cards) == 1
        card = cards[0]
        assert card.pan == SEED_CARD_PANS[dni]
        assert Card.objects.find_by_pan(SEED_CARD_PANS[dni]) == card
        assert card.type == "DEBIT"
        assert card.status == "ACTIVE"
        assert card.alias == "Kofre Debit"
        assert card.bank == "Kofre Bank"
        assert card.pin == "4321"
        today = date.today()
        assert card.expire_date.year == today.year + 3
        assert card.expire_date.month == today.month
        assert (card.expire_date + timedelta(days=1)).month != today.month


def _luhn_valid(pan):
    total = 0
    for i, c in enumerate(reversed(pan)):
        d = int(c)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def test_seed_cards_use_luhn_valid_non_reserved_pans():
    reserved = {"4111111111111111", "5500000000000004", "4000000000000002", "5105105105105100"}
    assert set(SEED_CARD_PANS) == set(CUSTOMER_DNIS)
    for pan in SEED_CARD_PANS.values():
        assert len(pan) == 16 and pan.isdigit()
        assert _luhn_valid(pan)
        assert pan not in reserved


def test_generated_card_pin_is_printed_once_and_works(capsys):
    call_command("seed_users")
    out = capsys.readouterr().out
    match = re.search(r"Card PIN: (\d{4})", out)
    assert match, out
    card = _cards_of(User.objects.find_by_dni(CUSTOMER_DNIS[0]))[0]
    assert card.pin == match.group(1)
    assert out.count("Card PIN:") == 1


def test_invalid_card_pin_is_rejected():
    with pytest.raises(CommandError):
        call_command("seed_users", card_pin="12345")
    assert User.objects.count() == 0


def test_rerun_creates_no_duplicate_cards_or_users():
    call_command("seed_users")
    call_command("seed_users")

    assert User.objects.count() == len(SEED_USERS)
    assert Card.objects.count() == len(CUSTOMER_DNIS)


def test_customer_without_card_gets_one_on_rerun(capsys):
    call_command("seed_users", password="Seed_Pass1!", pin="654321")
    Card.objects.all().delete()  # a database seeded before cards existed
    capsys.readouterr()

    call_command("seed_users", card_pin="1111")
    out = capsys.readouterr().out

    for dni in CUSTOMER_DNIS:
        cards = _cards_of(User.objects.find_by_dni(dni))
        assert len(cards) == 1
        assert cards[0].pan == SEED_CARD_PANS[dni]
        assert cards[0].pin == "1111"
        assert SEED_CARD_PANS[dni] in out
    assert User.objects.count() == len(SEED_USERS)
    assert "Password:" not in out  # no new users, so no credentials are printed
    assert "Card PIN: 1111" in out


def test_admin_and_auditor_never_get_a_card():
    call_command("seed_users")
    for _, dni, _, _, _, role in SEED_USERS:
        if role != CUSTOMER:
            assert _cards_of(User.objects.find_by_dni(dni)) == []

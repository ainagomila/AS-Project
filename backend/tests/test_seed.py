import pytest
from django.core.management import call_command

from banking.models import Account
from iam.models import User
from iam.management.commands.seed_users import SEED_USERS

pytestmark = pytest.mark.django_db


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

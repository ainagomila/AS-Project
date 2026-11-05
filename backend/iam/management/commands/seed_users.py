import calendar
import secrets
import string
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from banking.models import Account, Card
from common import ids
from common import validators as v
from common.errors import AppError
from iam.models import ADMIN, AUDITOR, CUSTOMER, OPERATIONS
from iam.services import create_initial_account, create_user_record, find_by_dni

# Fictitious people for local demos and manual testing. The DNIs carry a valid
# control letter; the phone numbers and the .test e-mail domain are reserved.
SEED_USERS = [
    ("Ana Blanco", "10000001S", "ana.blanco@kofre.test", "+34600000001", "female", CUSTOMER),
    ("Bernat Puig", "10000002Q", "bernat.puig@kofre.test", "+34600000002", "male", CUSTOMER),
    ("Carla Admin", "10000003V", "carla.admin@kofre.test", "+34600000003", "female", ADMIN),
    ("Dani Auditor", "10000004H", "dani.auditor@kofre.test", "+34600000004", "other", AUDITOR),
    ("Elena Operations", "10000005L", "elena.operations@kofre.test", "+34600000005", "female", OPERATIONS),
]
# One debit card per seeded customer. The PANs are Luhn-valid and are not among
# the numbers the README reserves for manual testing.
SEED_CARD_PANS = {
    "10000001S": "4539621704882252",
    "10000002Q": "5285913046120738",
}
CARD_ALIAS = "Kofre Debit"
CARD_BANK = "Kofre Bank"
BIRTHDATE = "1995-04-10"


def _generate_password():
    # One of each class the password policy asks for, then random filler.
    alphabet = string.ascii_letters + string.digits
    filler = "".join(secrets.choice(alphabet) for _ in range(12))
    return f"Kf{filler}7!"


def _generate_pin():
    return f"{secrets.randbelow(10**6):06d}"


def _generate_card_pin():
    return f"{secrets.randbelow(10**4):04d}"


def _card_expiry(today):
    """Last day of the month, three years from today."""
    year = today.year + 3
    return date(year, today.month, calendar.monthrange(year, today.month)[1])


def _add_seed_card(account, pan, card_pin, expiry):
    """Creates the seed card on the account. Returns False if it is already there."""
    existing = Card.objects.find_by_pan(pan)
    if existing is not None:
        if existing.account_id == account.id:
            return False
        raise CommandError(f"Card {pan} already belongs to another account")
    card = Card(
        id=ids.generate("CARD"),
        pan=pan,
        expire_date=expiry,
        alias=CARD_ALIAS,
        bank=CARD_BANK,
        type="DEBIT",
        status="ACTIVE",
        account_id=account.id,
    )
    card.pin = card_pin
    card.save()
    return True


class Command(BaseCommand):
    help = (
        "Create demo users (two customers, an admin, an auditor and operations user), each with the "
        "initial 100 EUR account; the customers also get one debit card. Users that "
        "already exist are left unchanged, but a customer without its seed card gets "
        "one. No credentials are hard-coded: pass --password/--pin/--card-pin or "
        "random ones are generated and printed once."
    )

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Password for every seeded user (default: random).")
        parser.add_argument("--pin", help="6-digit user PIN for every seeded user (default: random).")
        parser.add_argument(
            "--card-pin", help="4-digit PIN for every seeded card (default: random)."
        )

    def handle(self, *args, password=None, pin=None, card_pin=None, **options):
        password = password or _generate_password()
        pin = pin or _generate_pin()
        card_pin = card_pin or _generate_card_pin()
        try:
            v.validate_card_pin(card_pin)
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        expiry = _card_expiry(date.today())

        created = []  # (dni, role, name, iban, pan or None)
        users_created = False
        cards_added = False
        for name, dni, email, phone, gender, role in SEED_USERS:
            pan = SEED_CARD_PANS.get(dni)
            user = find_by_dni(dni)
            if user is None:
                try:
                    with transaction.atomic():
                        user = create_user_record(
                            name, dni, email, phone, password, BIRTHDATE, gender, pin
                        )
                        user.role = role
                        user.save()
                        account = create_initial_account(user)
                        if pan is not None:
                            _add_seed_card(account, pan, card_pin, expiry)
                except AppError as exc:
                    raise CommandError(f"Could not create {dni}: {exc.code} {exc}") from None
                created.append((dni, role, name, account.iban, pan))
                users_created = True
                cards_added = cards_added or pan is not None
                continue

            added = False
            if pan is not None:
                account = Account.objects.filter(user_id=user.id).order_by("id").first()
                if account is None:
                    raise CommandError(f"{dni} has no account to add the card to")
                with transaction.atomic():
                    added = _add_seed_card(account, pan, card_pin, expiry)
            if added:
                created.append((dni, role, name, account.iban, pan))
                cards_added = True
            else:
                self.stdout.write(f"{dni} ({role}) already exists, left unchanged")

        if not created:
            self.stdout.write("Nothing to do.")
            return
        self.stdout.write("")
        for dni, role, name, iban, pan in created:
            line = f"  {dni}  {role:<9} {name:<14} {iban}"
            if pan is not None:
                line += f"  card {pan}"
            self.stdout.write(line)
        self.stdout.write("")
        if users_created:
            self.stdout.write(f"Password: {password}")
            self.stdout.write(f"User PIN: {pin}")
        if cards_added:
            self.stdout.write(f"Card PIN: {card_pin}")
        self.stdout.write(self.style.WARNING("Shown only now; local demo use only."))

import secrets
import string

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from common.errors import AppError
from iam.models import ADMIN, AUDITOR, CUSTOMER
from iam.services import create_initial_account, create_user_record, find_by_dni

# Fictitious people for local demos and manual testing. The DNIs carry a valid
# control letter; the phone numbers and the .test e-mail domain are reserved.
SEED_USERS = [
    ("Ana Blanco", "10000001S", "ana.blanco@kofre.test", "+34600000001", "female", CUSTOMER),
    ("Bernat Puig", "10000002Q", "bernat.puig@kofre.test", "+34600000002", "male", CUSTOMER),
    ("Carla Admin", "10000003V", "carla.admin@kofre.test", "+34600000003", "female", ADMIN),
    ("Dani Auditor", "10000004H", "dani.auditor@kofre.test", "+34600000004", "other", AUDITOR),
]
BIRTHDATE = "1995-04-10"


def _generate_password():
    # One of each class the password policy asks for, then random filler.
    alphabet = string.ascii_letters + string.digits
    filler = "".join(secrets.choice(alphabet) for _ in range(12))
    return f"Kf{filler}7!"


def _generate_pin():
    return f"{secrets.randbelow(10**6):06d}"


class Command(BaseCommand):
    help = (
        "Create demo users (two customers, an admin and an auditor), each with the "
        "initial 100 EUR account. Users that already exist are left unchanged. "
        "No credentials are hard-coded: pass --password/--pin or random ones are "
        "generated and printed once."
    )

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Password for every seeded user (default: random).")
        parser.add_argument("--pin", help="6-digit user PIN for every seeded user (default: random).")

    def handle(self, *args, password=None, pin=None, **options):
        password = password or _generate_password()
        pin = pin or _generate_pin()

        created = []
        for name, dni, email, phone, gender, role in SEED_USERS:
            if find_by_dni(dni) is not None:
                self.stdout.write(f"{dni} ({role}) already exists, left unchanged")
                continue
            try:
                with transaction.atomic():
                    user = create_user_record(
                        name, dni, email, phone, password, BIRTHDATE, gender, pin
                    )
                    user.role = role
                    user.save()
                    account = create_initial_account(user)
            except AppError as exc:
                raise CommandError(f"Could not create {dni}: {exc.code} {exc}") from None
            created.append((dni, role, name, account.iban))

        if not created:
            self.stdout.write("Nothing to do.")
            return
        self.stdout.write("")
        for dni, role, name, iban in created:
            self.stdout.write(f"  {dni}  {role:<9} {name:<14} {iban}")
        self.stdout.write("")
        self.stdout.write(f"Password: {password}")
        self.stdout.write(f"User PIN: {pin}")
        self.stdout.write(self.style.WARNING("Shown only now; local demo use only."))

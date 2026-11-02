from django.core.management.base import BaseCommand, CommandError

from iam.models import ROLES, User


class Command(BaseCommand):
    help = "Give a role (customer, admin, auditor or operations) to an already registered user."

    def add_arguments(self, parser):
        parser.add_argument("dni")
        parser.add_argument("role", choices=[name for name, _ in ROLES])

    def handle(self, *args, dni, role, **options):
        user = User.objects.find_by_dni(dni)
        if user is None:
            raise CommandError(f"No user with DNI {dni}. Register the user first.")
        user.role = role
        user.save(update_fields=["role"])
        self.stdout.write(f"{dni} is now {role}")

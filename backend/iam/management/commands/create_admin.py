from django.core.management.base import BaseCommand, CommandError

from iam.models import User


class Command(BaseCommand):
    help = "Give the administrator role to an already registered user."

    def add_arguments(self, parser):
        parser.add_argument("dni")

    def handle(self, *args, dni, **options):
        user = User.objects.find_by_dni(dni)
        if user is None:
            raise CommandError(f"No user with DNI {dni}. Register the user first.")
        user.is_admin = True
        user.save()
        self.stdout.write(f"{dni} is now an administrator")

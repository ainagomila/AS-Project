from django.core.management.base import BaseCommand, CommandError

from iam.models import Role, User


class Command(BaseCommand):
    help = "Give the administrator role to an already registered user."

    def add_arguments(self, parser):
        parser.add_argument("dni")
        parser.add_argument(
            "--role",
            choices=[r.value for r in Role],
            default=Role.ADMIN,
            help="Role to assign (default: ADMIN).",
        )

    def handle(self, *args, dni, role, **options):
        user = User.objects.filter(dni=dni).first()
        if user is None:
            raise CommandError(f"No user with DNI {dni}. Register the user first.")
        user.role = role
        user.save(update_fields=["role"])
        self.stdout.write(f"{dni} is now {role}")

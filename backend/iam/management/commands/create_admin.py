from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Give the administrator role to an already registered user (same as: set_role <dni> admin)."

    def add_arguments(self, parser):
        parser.add_argument("dni")

    def handle(self, *args, dni, **options):
        call_command("set_role", dni, "admin", stdout=self.stdout)

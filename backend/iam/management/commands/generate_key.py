import base64
import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a local AES-256 key file for field encryption (development only)."

    def handle(self, *args, **options):
        path = Path(settings.SECURITY_ENCRYPTION_KEY_FILE)
        if path.exists():
            raise CommandError(f"{path} already exists; delete it first to rotate the key.")
        path.parent.mkdir(parents=True, exist_ok=True)
        key = base64.b64encode(os.urandom(32)).decode("ascii")
        path.write_text(json.dumps({"keyBase64": key}), encoding="utf-8")
        self.stdout.write(f"Key written to {path}")

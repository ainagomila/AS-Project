import base64
import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from common import crypto


def _new_key():
    return base64.b64encode(os.urandom(32)).decode("ascii")


class Command(BaseCommand):
    help = (
        "Create the local keyring for field encryption (development only). "
        "With --rotate, add a new current key; old keys stay so existing data still decrypts."
    )

    def add_arguments(self, parser):
        parser.add_argument("--rotate", action="store_true")

    def handle(self, *args, rotate, **options):
        path = Path(settings.SECURITY_ENCRYPTION_KEY_FILE)
        if not rotate:
            if path.exists():
                raise CommandError(f"{path} already exists; use --rotate to add a new key.")
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {"current": "k1", "keys": {"k1": _new_key()}, "indexKeyBase64": _new_key()}
        else:
            data = crypto.read_keyring_file(path)
            if not data:
                raise CommandError(f"{path} does not exist or is not valid JSON.")
            ring = crypto.parse_keyring(data)
            keys = {kid: base64.b64encode(key).decode("ascii") for kid, key in ring.keys.items()}
            kid = next(f"k{n}" for n in range(len(keys) + 1, 1000) if f"k{n}" not in keys)
            keys[kid] = _new_key()
            # The index key is written out so lookups keep working whatever keys are added.
            index_key = base64.b64encode(ring.index_key).decode("ascii")
            data = {"current": kid, "keys": keys, "indexKeyBase64": index_key}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        path.chmod(0o600)
        self.stdout.write(f"Keyring written to {path} (current key {data['current']})")

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.db import migrations, models

from banking.models import normalize_pan, pan_blind_index
from common import crypto


def _context(card, column):
    return crypto.context("banking_card", column, card.pk)


def encrypt_cards(apps, schema_editor):
    Card = apps.get_model("banking", "Card")
    for card in Card.objects.all():
        pan = normalize_pan(card.pan)
        card.pan_enc = crypto.encrypt(pan, _context(card, "pan_enc"))
        card.pan_index = pan_blind_index(pan)
        pin = crypto.decrypt_legacy(card.pin_iv, card.pin_ciphertext, card.pin_tag)
        card.pin_enc = crypto.encrypt(pin, _context(card, "pin_enc"))
        card.save()


def decrypt_cards(apps, schema_editor):
    Card = apps.get_model("banking", "Card")
    key = crypto._keyring().keys["k1"]
    b64 = lambda b: base64.b64encode(b).decode("ascii")  # noqa: E731
    for card in Card.objects.all():
        card.pan = crypto.decrypt(card.pan_enc, _context(card, "pan_enc"))
        pin = crypto.decrypt(card.pin_enc, _context(card, "pin_enc"))
        iv = os.urandom(12)
        sealed = AESGCM(key).encrypt(iv, pin.encode("utf-8"), None)
        card.pin_iv, card.pin_ciphertext, card.pin_tag = b64(iv), b64(sealed[:-16]), b64(sealed[-16:])
        card.save()


class Migration(migrations.Migration):

    dependencies = [
        ('banking', '0003_remove_card_cvv'),
    ]

    operations = [
        # Old columns become nullable so that the migration can be reversed.
        migrations.AlterField('card', 'pan', models.CharField(db_index=True, max_length=32, null=True)),
        migrations.AlterField('card', 'pin_iv', models.CharField(max_length=32, null=True)),
        migrations.AlterField('card', 'pin_ciphertext', models.TextField(null=True)),
        migrations.AlterField('card', 'pin_tag', models.CharField(max_length=32, null=True)),
        migrations.AddField('card', 'pan_enc', models.TextField(default=''), preserve_default=False),
        migrations.AddField('card', 'pan_index', models.CharField(max_length=64, null=True)),
        migrations.AddField('card', 'pin_enc', models.TextField(default=''), preserve_default=False),
        migrations.RunPython(encrypt_cards, decrypt_cards),
        migrations.RemoveField('card', 'pan'),
        migrations.RemoveField('card', 'pin_iv'),
        migrations.RemoveField('card', 'pin_ciphertext'),
        migrations.RemoveField('card', 'pin_tag'),
        migrations.AlterField('card', 'pan_index', models.CharField(max_length=64, unique=True)),
    ]

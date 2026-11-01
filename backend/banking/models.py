import re

from django.db import models

from common import crypto


class Account(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    iban = models.CharField(max_length=34, db_index=True)
    name = models.CharField(max_length=255)
    bank = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)
    # Plain reference, as in the original: deleting a user leaves the account.
    user_id = models.CharField(max_length=32, db_index=True)


def normalize_pan(pan):
    return re.sub(r"\s+", "", pan or "")


def pan_blind_index(pan):
    return crypto.blind_index(normalize_pan(pan), "banking_card.pan_index")


class CardManager(models.Manager):
    def find_by_pan(self, pan):
        return self.filter(pan_index=pan_blind_index(pan)).first()


class Card(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    # PAN and PIN are encrypted (common/crypto.py); the PAN blind index serves
    # lookups. The CVV is never stored: the verifier service checks it when the
    # card is added.
    pan_enc = models.TextField()
    pan_index = models.CharField(max_length=64, unique=True)
    expire_date = models.DateField()
    alias = models.CharField(max_length=255)
    bank = models.CharField(max_length=255)
    type = models.CharField(max_length=8)
    status = models.CharField(max_length=8)
    pin_enc = models.TextField()
    account_id = models.CharField(max_length=32, db_index=True)
    objects = CardManager()

    pan = crypto.encrypted("pan_enc", normalize=normalize_pan, index=("pan_index", pan_blind_index))
    pin = crypto.encrypted("pin_enc")

    @property
    def expire_date_card_format(self):
        return self.expire_date.strftime("%m/%y")

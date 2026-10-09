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


class Card(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    # PAN and CVV are stored in clear; only the PIN is encrypted, as in the original.
    pan = models.CharField(max_length=32, db_index=True)
    cvv = models.CharField(max_length=4)
    expire_date = models.DateField()
    alias = models.CharField(max_length=255)
    bank = models.CharField(max_length=255)
    type = models.CharField(max_length=8)
    status = models.CharField(max_length=8)
    pin_iv = models.CharField(max_length=32)
    pin_ciphertext = models.TextField()
    pin_tag = models.CharField(max_length=32)
    account_id = models.CharField(max_length=32, db_index=True)

    @property
    def pin(self):
        return crypto.decrypt(self.pin_iv, self.pin_ciphertext, self.pin_tag)

    @pin.setter
    def pin(self, plain):
        self.pin_iv, self.pin_ciphertext, self.pin_tag = crypto.encrypt(plain)

    @property
    def expire_date_card_format(self):
        return self.expire_date.strftime("%m/%y")

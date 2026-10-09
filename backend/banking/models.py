from django.db import models


class Account(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    iban = models.CharField(max_length=34, db_index=True)
    name = models.CharField(max_length=255)
    bank = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)
    # Plain reference, as in the original: deleting a user leaves the account.
    user_id = models.CharField(max_length=32, db_index=True)

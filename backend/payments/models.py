from django.db import models


class Payment(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    emitter_id = models.CharField(max_length=34, db_index=True)   # source IBAN
    receiver_id = models.CharField(max_length=34, db_index=True)  # destination IBAN
    type = models.CharField(max_length=16)
    categories = models.JSONField(default=list)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)
    concept = models.CharField(max_length=255)
    payment_date = models.CharField(max_length=40)  # ISO-8601 instant, as stored originally
    status = models.CharField(max_length=16)
    failure_reason = models.CharField(max_length=255, null=True)

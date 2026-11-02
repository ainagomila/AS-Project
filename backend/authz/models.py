from django.db import models


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionError("Audit events cannot be changed")

    def delete(self):
        raise PermissionError("Audit events cannot be deleted")


class AuditEvent(models.Model):
    """One access decision the policy asked to record.

    Append-only: rows cannot be updated or deleted through the ORM. Identities
    are stored as internal ids, never as DNI or IBAN, and are kept as plain
    strings so the trail survives when a user is deleted.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    subject_id = models.CharField(max_length=32, blank=True)
    subject_role = models.CharField(max_length=16)
    action = models.CharField(max_length=32)
    resource_type = models.CharField(max_length=32)
    resource_id = models.CharField(max_length=32, blank=True)
    decision = models.CharField(max_length=16)
    rule = models.CharField(max_length=128)
    status_code = models.PositiveSmallIntegerField()
    client_ip = models.CharField(max_length=45, blank=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError("Audit events cannot be changed")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit events cannot be deleted")

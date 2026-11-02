from django.db import models
from django.utils import timezone

from common import crypto


class Role(models.TextChoices):
    """Application roles.

    - USER: a normal customer. Can only act on their own accounts and cards.
    - ADMIN: full management access (users, accounts, cards, settings) plus the
      ability to grant and revoke roles.
    - AUDITOR: read-only access to the same entities an admin can read, but no
      write operations. Separation of duties for compliance reviews.
    """

    USER = "USER", "User"
    ADMIN = "ADMIN", "Administrator"
    AUDITOR = "AUDITOR", "Auditor"

class User(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    dni = models.CharField(max_length=16, db_index=True)
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    phone_prefix = models.CharField(max_length=8)
    phone_number = models.CharField(max_length=16)
    birthdate = models.DateField()
    gender = models.CharField(max_length=8)

    # Password and PIN are stored with reversible encryption, as in the original.
    password_iv = models.CharField(max_length=32)
    password_ciphertext = models.TextField()
    password_tag = models.CharField(max_length=32)
    pin_iv = models.CharField(max_length=32)
    pin_ciphertext = models.TextField()
    pin_tag = models.CharField(max_length=32)

    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.USER, db_index=True
    )
    is_active = models.BooleanField(default=True)

    # Login throttling / lockout (hardening, not part of the original baseline).
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    @property
    def is_admin(self):
        """Backwards-compatible convenience: true only for the ADMIN role."""
        return self.role == Role.ADMIN

    @property
    def is_staff(self):
        """True for every role that may enter the admin console."""
        return self.role in (Role.ADMIN, Role.AUDITOR)

    @property
    def password(self):
        return crypto.decrypt(self.password_iv, self.password_ciphertext, self.password_tag)

    @password.setter
    def password(self, plain):
        self.password_iv, self.password_ciphertext, self.password_tag = crypto.encrypt(plain)

    @property
    def pin(self):
        return crypto.decrypt(self.pin_iv, self.pin_ciphertext, self.pin_tag)

    @pin.setter
    def pin(self, plain):
        self.pin_iv, self.pin_ciphertext, self.pin_tag = crypto.encrypt(plain)

    @property
    def phone(self):
        return self.phone_prefix + self.phone_number

    def purge_expired_sessions(self):
        self.sessions.filter(expires_at__lt=timezone.now()).delete()

    def check_session(self, token):
        self.purge_expired_sessions()
        return self.sessions.filter(token=token, expires_at__gte=timezone.now()).exists()


class Session(models.Model):
    token = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    expires_at = models.DateTimeField()

class AuditLog(models.Model):
    """Append-only record of sensitive administrative actions (X5 / B13)."""

    id = models.CharField(primary_key=True, max_length=32)
    actor_id = models.CharField(max_length=32, db_index=True)
    actor_dni = models.CharField(max_length=16)
    action = models.CharField(max_length=64, db_index=True)
    target_type = models.CharField(max_length=32)
    target_id = models.CharField(max_length=64, default="", blank=True)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class SystemSetting(models.Model):
    """Key/value store for advanced administrator configuration."""

    key = models.CharField(primary_key=True, max_length=64)
    value = models.JSONField()
    description = models.CharField(max_length=255, default="", blank=True)
    updated_at = models.DateTimeField(auto_now=True)

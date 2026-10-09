from django.db import models
from django.utils import timezone

from common import crypto


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

    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

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

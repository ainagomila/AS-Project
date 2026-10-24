from django.db import models
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser

from common import crypto

class UserManager(BaseUserManager):
    def create_user(self, dni, email, password=None, **extra_fields):
        if not email: raise ValueError("Users must have an email address")
        email=self.normalize_email(email)
        user = self.model(dni=dni, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
class User(AbstractBaseUser):
    id = models.CharField(primary_key=True, max_length=32)
    email = models.CharField(max_length=255)    
    dni = models.CharField(max_length=16, db_index=True, unique=True)
    name = models.CharField(max_length=255)
    phone_prefix = models.CharField(max_length=8)
    phone_number = models.CharField(max_length=16)
    birthdate = models.DateField()
    gender = models.CharField(max_length=8)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    objects = UserManager()
    password = models.CharField(max_length = 128)
    pin_iv = models.CharField(max_length=32)
    pin_ciphertext = models.TextField()
    pin_tag = models.CharField(max_length=32)
    USERNAME_FIELD = 'dni'
    REQUIRED_FIELDS = []

    
    def __str__(self):
        return self.email
    
    def set_password(self, raw):
          self.password = make_password(raw)

    
    def check_password(self, raw):
        return check_password(raw, self.password)

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


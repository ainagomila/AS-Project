import re

from django.db import models
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser

from common import crypto, ids


def normalize_dni(dni):
    return re.sub(r"\s+", "", dni or "").upper()


def dni_blind_index(dni):
    return crypto.blind_index(normalize_dni(dni), "iam_user.dni_index")


def phone_blind_index(prefix, number):
    return crypto.blind_index(f"{prefix}{number}", "iam_user.phone_index")


class UserManager(BaseUserManager):
    def create_user(self, dni, email, password=None, **extra_fields):
        if not email: raise ValueError("Users must have an email address")
        email=self.normalize_email(email)
        user = self.model(id=ids.generate("USER"), dni=dni, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def find_by_dni(self, dni):
        return self.filter(dni_index=dni_blind_index(dni)).first()

    def get_by_natural_key(self, username):
        # Login (ModelBackend) passes the DNI typed by the user.
        return self.get(dni_index=dni_blind_index(username))

    def phone_exists(self, prefix, number):
        return self.filter(phone_index=phone_blind_index(prefix, number)).exists()


class User(AbstractBaseUser):
    id = models.CharField(primary_key=True, max_length=32)
    # DNI, email and phone number are encrypted (common/crypto.py); the blind
    # indexes serve lookups and uniqueness.
    dni_enc = models.TextField()
    dni_index = models.CharField(max_length=64, unique=True)
    email_enc = models.TextField()
    name = models.CharField(max_length=255)
    phone_prefix = models.CharField(max_length=8)
    phone_number_enc = models.TextField()
    phone_index = models.CharField(max_length=64, db_index=True)
    birthdate = models.DateField()
    gender = models.CharField(max_length=8)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    objects = UserManager()
    password = models.CharField(max_length = 128)
    pin = models.CharField(max_length=128)
    USERNAME_FIELD = 'dni_index'
    REQUIRED_FIELDS = []

    dni = crypto.encrypted("dni_enc", normalize=normalize_dni, index=("dni_index", dni_blind_index))
    email = crypto.encrypted("email_enc")
    phone_number = crypto.encrypted("phone_number_enc")

    def __str__(self):
        return self.id

    def set_password(self, raw):
          self.password = make_password(raw)


    def check_password(self, raw):
        return check_password(raw, self.password)

    def set_pin(self, raw):
        self.pin = make_password(raw)

    def check_pin(self, raw):
        return check_password(raw, self.pin)

    def set_phone(self, prefix, number):
        self.phone_prefix, self.phone_number = prefix, number
        self.phone_index = phone_blind_index(prefix, number)

    @property
    def phone(self):
        return self.phone_prefix + self.phone_number

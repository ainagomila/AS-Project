import base64
import secrets
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application
from rest_framework.test import APIClient

from common import crypto
from iam.models import User

PASSWORD = "Secret_123"
PIN = "123456"
# Valid Spanish DNIs (control letter checked).
DNI_A = "12345678Z"
DNI_B = "87654321X"


@pytest.fixture(autouse=True)
def encryption_key(settings):
    settings.SECURITY_ENCRYPTION_KEY_FILE = ""
    settings.SECURITY_ENCRYPTION_KEY_BASE64 = base64.b64encode(b"k" * 32).decode()
    crypto._keyring.cache_clear()
    yield
    crypto._keyring.cache_clear()


@pytest.fixture(autouse=True)
def clear_lockouts():
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


def register_payload(dni=DNI_A, phone="+34600123456", **overrides):
    payload = {
        "name": "Ana Blanco",
        "dni": dni,
        "email": f"user{dni[:4]}@example.com",
        "phone": phone,
        "password": PASSWORD,
        "birthdate": "1995-04-10",
        "gender": "female",
        "pin": PIN,
    }
    payload.update(overrides)
    return payload


class Actor:
    """A registered user plus a client that sends their token."""

    def __init__(self, dni, phone):
        self.dni = dni
        self.client = APIClient()
        response = self.client.post("/auth/register", register_payload(dni, phone), format="json")
        assert response.status_code == 201, response.content
        app, _ = Application.objects.get_or_create(
            client_id="kofre-test-api",
            defaults={
                "name": "tests",
                "client_type": Application.CLIENT_PUBLIC,
                "authorization_grant_type": Application.GRANT_AUTHORIZATION_CODE,
                "redirect_uris": "https://localhost:5173/callback",
            },
        )
        self.token = AccessToken.objects.create(
            user=User.objects.get_by_natural_key(dni),
            application=app,
            token=secrets.token_urlsafe(32),
            expires=timezone.now() + timedelta(minutes=5),
            scope="banking",
        ).token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def url(self, suffix=""):
        return f"/users/{self.dni}{suffix}"

    def iban(self):
        return self.client.get(self.url("/accounts")).json()["accounts"][0]["iban"]


@pytest.fixture
def ana(db):
    return Actor(DNI_A, "+34600123456")


@pytest.fixture
def bob(db):
    return Actor(DNI_B, "+34600654321")

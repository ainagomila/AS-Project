import base64

import pytest
from rest_framework.test import APIClient

from common import crypto

PASSWORD = "Secret_123"
PIN = "123456"
# Valid Spanish DNIs (control letter checked).
DNI_A = "12345678Z"
DNI_B = "87654321X"


@pytest.fixture(autouse=True)
def encryption_key(settings):
    settings.SECURITY_ENCRYPTION_KEY_FILE = ""
    settings.SECURITY_ENCRYPTION_KEY_BASE64 = base64.b64encode(b"k" * 32).decode()
    crypto._key.cache_clear()
    yield
    crypto._key.cache_clear()


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
        self.token = response.json()["token"]
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

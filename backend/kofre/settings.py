"""Django settings for the Kofre backend (local development only)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-kofre-local-development-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
    "iam",
    "banking",
    "payments",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "kofre.urls"
WSGI_APPLICATION = "kofre.wsgi.application"
APPEND_SLASH = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "kofredb",
        "USER": "user",
        "PASSWORD": "password",
        "HOST": "db",
        "PORT": 5432
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "EXCEPTION_HANDLER": "common.errors.exception_handler",
    "UNAUTHENTICATED_USER": None,
    "UNAUTHENTICATED_TOKEN": None,
    "COERCE_DECIMAL_TO_STRING": False,
}

# Same behaviour as the original WebConfig: listed origins with credentials.
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]

# Field encryption key (see common/crypto.py). The key file wins over the env var.
SECURITY_ENCRYPTION_KEY_FILE = os.environ.get(
    "SECURITY_ENCRYPTION_KEY_FILE", str(BASE_DIR / ".env.d" / "encryptionKey64.json")
)
SECURITY_ENCRYPTION_KEY_BASE64 = os.environ.get("SECURITY_ENCRYPTION_KEY_BASE64", "")

# Card verifier service (verifier-backend), reachable only on the internal network.
VERIFIER_URL = os.environ.get("VERIFIER_URL", "http://localhost:5678")

SESSION_TTL_SECONDS = 86_400  # 24h

"""Django settings for the Kofre backend (local development only)."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-kofre-local-development-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]
AUTH_USER_MODEL = "iam.User"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "corsheaders",
    "common",
    "rest_framework",
    "iam",
    "banking",
    "payments",
    "oauth2_provider",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ],
        },
    },
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
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,https://localhost:5173",
    ).split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]

# Base URL of the Vue app: the OAuth redirect URI and the login page links use it.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://localhost:5173")

# Field encryption key (see common/crypto.py). The key file wins over the env var.
SECURITY_ENCRYPTION_KEY_FILE = os.environ.get(
    "SECURITY_ENCRYPTION_KEY_FILE", str(BASE_DIR / ".env.d" / "encryptionKey64.json")
)
SECURITY_ENCRYPTION_KEY_BASE64 = os.environ.get("SECURITY_ENCRYPTION_KEY_BASE64", "")

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]


def _load_oidc_key():
    """OIDC RSA private key: file (default .env.d/oidc.key) or environment variable."""
    path = Path(os.environ.get("OIDC_RSA_PRIVATE_KEY_FILE", BASE_DIR / ".env.d" / "oidc.key"))
    key = path.read_text() if path.is_file() else os.environ.get("OIDC_RSA_PRIVATE_KEY", "")
    if not key:
        raise ImproperlyConfigured(
            "Missing OIDC key. Generate it with: "
            "mkdir -p backend/.env.d && openssl genrsa -out backend/.env.d/oidc.key 2048"
        )
    return key


OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 300,
    "SCOPES": {"openid": "OpenID Connect", "banking": "Access to the bank API"},
    "OIDC_ENABLED": True,
    "OIDC_RSA_PRIVATE_KEY": _load_oidc_key(),
    "OIDC_RP_INITIATED_LOGOUT_ENABLED": True,
    "OIDC_RP_INITIATED_LOGOUT_ALWAYS_PROMPT": False,  # we always send id_token_hint
    "PKCE_REQUIRED": True,                      # already the default; explicit on purpose
    "ALLOWED_REDIRECT_URI_SCHEMES": ["https"],  # HTTPS redirect URIs only
    "REFRESH_TOKEN_EXPIRE_SECONDS": 300,        # same as the access token: "extend" = 5 more minutes
    "ROTATE_REFRESH_TOKEN": True,
    "REFRESH_TOKEN_REUSE_PROTECTION": True,     # reusing an old refresh token revokes the session
    "REFRESH_TOKEN_GRACE_PERIOD_SECONDS": 0,    # required to store hashed tokens
    "COMPLIANT_BCP_RFC9700_TOKEN_STORAGE": True,  # store tokens hashed
    "COMPLIANT_BCP_RFC9700_PKCE_METHOD": True,    # rejects "plain" PKCE
    "COMPLIANT_BCP_RFC9700_PASSWORD_GRANT": True,
    "COMPLIANT_BCP_RFC9700_IMPLICIT_GRANT": True,
    "COMPLIANT_BCP_RFC9700_ACCESS_TOKEN_TRANSPORT": True,  # rejects the token in the query string
    "COMPLIANT_BCP_RFC9700_AUTHZ_RESPONSE_ISS": True,
    "OAUTH2_VALIDATOR_CLASS": "iam.oauth_validators.KofreOAuth2Validator",
}

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60  # only needed during login; renewing uses the refresh token
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SECURE = True

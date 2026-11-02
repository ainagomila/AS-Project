"""Runtime access to administrator-configurable system settings.

Only keys listed in DEFAULTS may be read or changed; the admin service refuses
anything else. A missing row falls back to the default, so the system keeps
working on a fresh database without any configuration.
"""

from .models import SystemSetting

DEFAULTS = {
    "SESSION_TTL_SECONDS": 86400,
    "REGISTRATION_ENABLED": True,
    "TRANSFER_MAX_AMOUNT": None,  # None means unlimited
    "MAINTENANCE_MODE": False,
    "LOGIN_MAX_ATTEMPTS": 5,
    "LOGIN_LOCKOUT_SECONDS": 900,
}

DESCRIPTIONS = {
    "SESSION_TTL_SECONDS": "Lifetime of a session token, in seconds.",
    "REGISTRATION_ENABLED": "Whether new users may register themselves.",
    "TRANSFER_MAX_AMOUNT": "Maximum amount for a single transfer (null = unlimited).",
    "MAINTENANCE_MODE": "When true, customer-facing write operations are blocked.",
    "LOGIN_MAX_ATTEMPTS": "Failed login attempts before the account is locked.",
    "LOGIN_LOCKOUT_SECONDS": "Duration of an account lockout, in seconds.",
}


def get_setting(key):
    obj = SystemSetting.objects.filter(key=key).first()
    return obj.value if obj is not None else DEFAULTS.get(key)


def all_settings():
    """Merged view of defaults and overrides, for the admin console."""
    merged = dict(DEFAULTS)
    for obj in SystemSetting.objects.all():
        merged[obj.key] = obj.value
    return merged


def set_setting(key, value):
    obj = SystemSetting.objects.filter(key=key).first()
    if obj is None:
        obj = SystemSetting(key=key, value=value, description=DESCRIPTIONS.get(key, ""))
    else:
        obj.value = value
    obj.save()
    return obj

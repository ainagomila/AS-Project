"""Lockout after repeated wrong secrets, per (DNI, client IP).

Each wrong PIN (any endpoint answering INVALID_PIN) or wrong login password
counts one failure. After LOCKOUT_MAX_FAILURES failures in LOCKOUT_WINDOW_SECONDS
(counted from the first one) further attempts are refused until the window ends:
429 on the API, an error on the login page. Counters live in the Django cache.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import BaseThrottle

from .seclog import security_event


def key(request, scope, dni):
    ip = request.META.get("REMOTE_ADDR", "")
    return f"lockout:{scope}:{str(dni or '').strip().upper()}:{ip}"


def is_locked(lock_key):
    return cache.get(lock_key, 0) >= settings.LOCKOUT_MAX_FAILURES


def record_failure(lock_key, request, event, **fields):
    """Count one failure and log it as `event`; the failure that reaches the limit also logs `lockout`.

    The lock key holds the DNI, so it is never logged.
    """
    cache.add(lock_key, 0, settings.LOCKOUT_WINDOW_SECONDS)
    try:
        count = cache.incr(lock_key)
    except ValueError:  # expired between add and incr
        cache.set(lock_key, 1, settings.LOCKOUT_WINDOW_SECONDS)
        count = 1
    security_event(event, request, logging.WARNING, **fields)
    if count == settings.LOCKOUT_MAX_FAILURES:
        security_event("lockout", request, logging.WARNING, after=event,
                       minutes=settings.LOCKOUT_WINDOW_SECONDS // 60, **fields)


def _body(request):
    return request.data if hasattr(request.data, "get") else {}


def pin_key(request, view_kwargs):
    """The DNI is in the URL (/users/{dni}/...) or, for reset-password, in the body."""
    return key(request, "pin", view_kwargs.get("dni") or _body(request).get("dni"))


class PinLockout(BaseThrottle):
    """Refuses requests that carry a PIN while their (DNI, IP) is locked out."""

    def allow_request(self, request, view):
        if "pin" not in _body(request):
            return True
        return not is_locked(pin_key(request, view.kwargs))

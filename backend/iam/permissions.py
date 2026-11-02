"""Centralised authorization policy (the "single place that decides access").

Every admin endpoint declares the roles that may call it through a DRF
permission class. Views no longer repeat an inline `is_admin` check, so a new
endpoint is protected by construction instead of by the author remembering to
copy the check (inventory item X2).
"""

from rest_framework.permissions import BasePermission

from common.errors import AppError

from .models import Role


class RequireRole(BasePermission):
    """Allow only the listed roles; answer 403 FORBIDDEN otherwise.

    Authentication (AnyTokenAuthentication) runs first and raises a 401 for a
    missing or invalid token, so by the time this runs `request.user` is always
    a live session's user.
    """

    roles = frozenset()

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if user is None:
            return False
        if user.role not in self.roles:
            raise AppError("FORBIDDEN", "No tens permisos suficients per a aquesta operació")
        return True


class IsAdmin(RequireRole):
    """Write access: administrators only."""

    roles = frozenset({Role.ADMIN})


class IsAdminOrAuditor(RequireRole):
    """Read access: administrators and auditors."""

    roles = frozenset({Role.ADMIN, Role.AUDITOR})


def assert_admin(user):
    """Synchronous guard for use inside service functions."""
    if user is None or user.role != Role.ADMIN:
        raise AppError("FORBIDDEN", "No tens permisos suficients per a aquesta operació")
    return user

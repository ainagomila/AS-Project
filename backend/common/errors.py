"""Error type, error codes and the DRF exception handler.

The response body and the code-to-status mapping reproduce the original
backend's AppError / ProblemMapper / GlobalExceptionHandler.
"""

import time
import traceback

from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response

from . import lockout

NOT_FOUND = {"USER_NOT_FOUND", "ACCOUNT_NOT_FOUND", "CARD_NOT_FOUND", "BANK_NOT_FOUND"}
CONFLICT = {
    "USER_ALREADY_EXISTS",
    "ACCOUNT_ALREADY_EXISTS",
    "CARD_ALREADY_EXISTS",
    "PASSWORD_ALREADY_EXISTS",
}
BAD_REQUEST = {
    "INVALID_DNI_FORMAT",
    "INVALID_EMAIL_FORMAT",
    "INVALID_PHONE_FORMAT",
    "INVALID_PIN_FORMAT",
    "INVALID_PASSWORD_FORMAT",
    "INVALID_IBAN_FORMAT",
    "INVALID_PAN_FORMAT",
    "INVALID_CVV_FORMAT",
    "INVALID_CARD",
    "INVALID_EXPIRATION_DATE_FORMAT",
    "INVALID_STATUS_FORMAT",
    "INVALID_STATUS",
    "INVALID_STATUS_REASON",
    "INVALID_TYPE_FORMAT",
    "INVALID_CREDENTIALS",
    "INVALID_CURRENCY",
    "INVALID_MONEY_AMOUNT",
    "DOMAIN_ERROR",
    "MISSING_FIELDS",
}
UNPROCESSABLE = {
    "INSUFFICIENT_FUNDS",
    "CARD_EXPIRED",
    "CARD_BLOCKED",
    "ACCOUNT_BLOCKED",
    "BANK_UNSUPPORTED",
    "USER_CANNOT_BE_MODIFIED",
    "APPLICATION_ERROR",
    "INVALID_PIN",
}
# UNAUTHORIZED maps to 403 in the original ProblemMapper. FORBIDDEN and
# USER_DISABLED are new codes introduced with the administrator role.
FORBIDDEN = {"UNAUTHORIZED", "FORBIDDEN", "USER_DISABLED"}

STATUS_BY_CODE = {
    **{c: 404 for c in NOT_FOUND},
    **{c: 409 for c in CONFLICT},
    **{c: 400 for c in BAD_REQUEST},
    **{c: 422 for c in UNPROCESSABLE},
    **{c: 403 for c in FORBIDDEN},
    "INFRA_ERROR": 500,
    "INTERNAL_ERROR": 500,
}


class AppError(Exception):
    """Business error. Unmapped codes answer 500, as in the original."""

    def __init__(self, code, message, metadata=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.metadata = metadata or {}

    @property
    def status(self):
        return STATUS_BY_CODE.get(self.code, 500)


class BareUnauthorized(Exception):
    """The original auth interceptor answers 401 with an empty body."""


def exception_handler(exc, context):
    if isinstance(exc, AppError) and exc.code == "INVALID_PIN":
        request = context["request"]
        user_id = getattr(request.user, "id", None)  # None on reset-password, which has no token
        lockout.record_failure(lockout.pin_key(request, context["kwargs"]), request, "pin.failure",
                               **({"user_id": user_id} if user_id else {}))
    if isinstance(exc, drf_exceptions.Throttled):
        message = "Massa intents. Torna-ho a provar més tard."
        return Response({"code": "TOO_MANY_ATTEMPTS", "message": message, "metadata": {}}, status=429)
    if isinstance(exc, AppError):
        return Response(
            {"code": exc.code, "message": exc.message, "metadata": exc.metadata},
            status=exc.status,
        )
    if isinstance(exc, BareUnauthorized):
        return Response(status=401)
    if isinstance(exc, (Http404, drf_exceptions.NotFound)):
        return Response(status=404)
    if isinstance(exc, drf_exceptions.MethodNotAllowed):
        return Response(status=405)
    # Everything else, including malformed bodies and domain exceptions the
    # services do not catch, is answered like the original's catch-all handler.
    traceback.print_exception(exc)
    return Response(
        {
            "error": "Internal Server Error",
            "message": str(exc),
            "timestamp": int(time.time() * 1000),
        },
        status=500,
    )

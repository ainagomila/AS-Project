"""Bearer-token authentication, ported from the original AuthInterceptor."""

from rest_framework.authentication import BaseAuthentication

from common.errors import AppError, BareUnauthorized

from . import services


class KofreTokenAuthentication(BaseAuthentication):
    """Validates the session token against the {dni} in the route, if any.

    Every failure answers 401 with an empty body, as the interceptor did.
    """

    check_route_dni = True

    def authenticate(self, request):
        header = request.headers.get("Authorization")
        if header is None or not header.startswith("Bearer "):
            raise BareUnauthorized()
        token = header[7:]

        kwargs = request.parser_context.get("kwargs", {}) if request.parser_context else {}
        dni = kwargs.get("dni") if self.check_route_dni else None
        try:
            user = services.validate(dni, token)
        except AppError:
            raise BareUnauthorized() from None

        if not user.is_active:
            raise AppError("USER_DISABLED", "L'usuari està deshabilitat")
        return user, token


class AnyTokenAuthentication(KofreTokenAuthentication):
    """For routes whose {dni} names a target user rather than the caller."""

    check_route_dni = False

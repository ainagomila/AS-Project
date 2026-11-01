"""Bearer-token authentication on top of django-oauth-toolkit."""

from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from common.errors import AppError, BareUnauthorized


class KofreTokenAuthentication(OAuth2Authentication):
    """Validates the DOT access token and, if the route has a {dni}, that it belongs to that user.

    Every failure answers 401 with an empty body, as before.
    """

    check_route_dni = True

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            raise BareUnauthorized()
        user, token = result

        kwargs = request.parser_context.get("kwargs", {}) if request.parser_context else {}
        dni = kwargs.get("dni") if self.check_route_dni else None
        if dni is not None and user.dni != dni:
            raise BareUnauthorized()

        if not user.is_active:
            raise AppError("USER_DISABLED", "L'usuari està deshabilitat")
        return user, token


class AnyTokenAuthentication(KofreTokenAuthentication):
    """For routes whose {dni} names a target user rather than the caller."""

    check_route_dni = False

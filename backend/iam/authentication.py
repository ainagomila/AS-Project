"""Bearer-token authentication on top of django-oauth-toolkit."""

from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from common.errors import BareUnauthorized


class KofreTokenAuthentication(OAuth2Authentication):
    """Validates the DOT access token. Every failure answers 401 with an empty body.

    It only establishes who the caller is. Whether they may act on the
    resource (the DNI in the URL, a disabled account, their role) is decided
    by the XACML policy through authz.pep.PolicyEnforcedView.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            raise BareUnauthorized()
        return result

"""Global middleware: browser security headers and maintenance mode.

These are the only two places that apply policy to every request. The
maintenance-mode check is path based (admin and auth routes stay reachable) and
defaults to off, so the baseline behaviour is unchanged until an administrator
turns it on.
"""

from django.http import JsonResponse

ALLOWED_PATHS = ("/admin", "/auth")


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "no-referrer"
        response["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        return response


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._blocked(request):
            return JsonResponse(
                {"code": "MAINTENANCE_MODE", "message": "Manteniment en curs", "metadata": {}},
                status=503,
            )
        return self.get_response(request)

    def _blocked(self, request):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return False
        if request.path.startswith(ALLOWED_PATHS):
            return False
        try:
            from iam.system_settings import get_setting

            return bool(get_setting("MAINTENANCE_MODE"))
        except Exception:
            return False

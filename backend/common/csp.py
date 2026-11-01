"""Content-Security-Policy header (Django 5.2 has no built-in CSP support).

Only the login page renders HTML. Its inline <style> and <script> carry the
per-request nonce (`request.csp_nonce`); the API's JSON gets the same strict policy.
"""

import secrets

from django.conf import settings


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        frontend = settings.FRONTEND_URL.rstrip("/")
        self.policy = (
            "default-src 'none'; "
            "script-src 'nonce-{nonce}'; "
            "style-src 'nonce-{nonce}' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self'; "
            # The login POST is redirected via /o/authorize/ to the Vue app's /callback.
            f"form-action 'self' {frontend}; "
            "frame-ancestors 'none'; "
            "base-uri 'none'"
        )

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        response.headers.setdefault(
            "Content-Security-Policy", self.policy.replace("{nonce}", request.csp_nonce)
        )
        return response

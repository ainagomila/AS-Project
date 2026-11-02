from django.conf import settings
from django.contrib.auth import views as auth_views

from common import lockout


class LoginView(auth_views.LoginView):
    """The OAuth login page, locked per (DNI, client IP) after repeated wrong passwords."""

    extra_context = {"frontend_url": settings.FRONTEND_URL}

    def post(self, request, *args, **kwargs):
        lock_key = lockout.key(request, "login", request.POST.get("username"))
        if lockout.is_locked(lock_key):
            context = self.get_context_data(form=self.get_form_class()(request), locked=True)
            return self.render_to_response(context, status=429)
        response = super().post(request, *args, **kwargs)
        if response.status_code != 302:  # the form was re-rendered: wrong DNI or password
            lockout.record_failure(lock_key)
        return response

from rest_framework.response import Response
from rest_framework.views import APIView

from common.http import text
from common.validators import has_text

from . import services
from .authentication import KofreTokenAuthentication


# ------------------------------------------------------------- /auth (public)

class RegisterView(APIView):
    def post(self, request):
        fields = ("name", "dni", "email", "phone", "password", "birthdate", "gender", "pin")
        body = services.register(**{f: text(request, f) for f in fields})
        return Response(body, status=201)


class ResetPasswordView(APIView):
    def post(self, request):
        services.update_password(
            text(request, "dni"), text(request, "pin"), text(request, "newPassword")
        )
        return Response(status=204)


# ------------------------------------------------------------- /users (token)

class AuthenticatedView(APIView):
    authentication_classes = [KofreTokenAuthentication]


class UserListView(AuthenticatedView):
    def get(self, request):
        return Response(services.list_users())


class UserDetailView(AuthenticatedView):
    def get(self, request, dni):
        return Response(services.get_user(dni))

    def patch(self, request, dni):
        pin = text(request, "pin")
        email, phone = text(request, "email"), text(request, "phone")
        password, new_pin = text(request, "password"), text(request, "newPin")

        # Each present field is applied in turn; the last result is returned.
        result = None
        if has_text(email):
            result = services.update_email(dni, pin, email)
        if has_text(phone):
            prefix, number = services.split_update_phone(phone)
            result = services.update_phone(dni, pin, prefix, number)
        if has_text(password):
            result = services.update_password(dni, pin, password, keep_token=request.auth)
        if has_text(new_pin):
            result = services.update_pin(dni, pin, new_pin)
        if result is None:
            # The original dereferences a null result here and answers 500.
            raise RuntimeError("No fields to update")
        return Response(result)

    def delete(self, request, dni):
        services.delete_user(dni, text(request, "pin"))
        return Response(status=204)


class VerifyPinView(AuthenticatedView):
    def post(self, request, dni):
        return Response(services.verify_pin(dni, text(request, "pin")))


class VerifyPasswordView(AuthenticatedView):
    def post(self, request, dni):
        return Response(services.verify_password(dni, text(request, "pin")))

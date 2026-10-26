"""Administrator endpoints (new in the Django port; not part of the original).

Each view checks the caller's admin flag inline.
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from banking.models import Account
from banking.services import account_response, find_by_iban
from common.errors import AppError
from payments.services import payments_for_account

from . import services
from .authentication import AnyTokenAuthentication
from .models import User


def admin_user_response(user):
    return {**services.user_response(user), "active": user.is_active}


def _target_user(dni):
    user = services.find_by_dni(dni)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    return user


class AdminView(APIView):
    authentication_classes = [AnyTokenAuthentication]


class AdminUserListView(AdminView):
    def get(self, request):
        if not request.user.is_admin:
            raise AppError("FORBIDDEN", "Cal ser administrador")
        return Response([admin_user_response(u) for u in User.objects.all()])


class AdminUserDetailView(AdminView):
    def patch(self, request, dni):
        if not request.user.is_admin:
            raise AppError("FORBIDDEN", "Cal ser administrador")
        user = _target_user(dni)
        active = request.data.get("active")
        if not isinstance(active, bool):
            raise AppError("MISSING_FIELDS", "Cal informar 'active' (true o false)")
        user.is_active = active
        user.save()
        if not active:
            services.revoke_tokens(user)
        return Response(admin_user_response(user))


class AdminUserAccountsView(AdminView):
    def get(self, request, dni):
        if not request.user.is_admin:
            raise AppError("FORBIDDEN", "Cal ser administrador")
        user = _target_user(dni)
        accounts = Account.objects.filter(user_id=user.id)
        return Response({"accounts": [account_response(a) for a in accounts]})


class AdminAccountTransfersView(AdminView):
    def get(self, request, dni, iban):
        if not request.user.is_admin:
            raise AppError("FORBIDDEN", "Cal ser administrador")
        user = _target_user(dni)
        account = find_by_iban(iban)
        if account is None or account.user_id != user.id:
            raise AppError("ACCOUNT_NOT_FOUND", "Compte inexistent")
        return Response(payments_for_account(account.iban))

"""Back-office endpoints for administrators and auditors.

Who may call what is decided by the XACML policy (authz/policies), not here:
administrators manage customer identities; auditors read accounts and
transfers, pseudonymised by the policy's masking obligation.

Users and accounts are addressed by their internal ids, never by DNI or IBAN,
so personal identifiers stay out of URLs and server logs.
"""

from django.db import transaction
from rest_framework.response import Response

from banking.models import Account
from common.errors import AppError
from payments.services import payments_for_account

from . import services
from . import admin_services
from .authentication import KofreTokenAuthentication
from .models import User
from authz.pep import PolicyEnforcedView


def _staff_user(user_id):
    user = User.objects.filter(id=user_id).first()
    if user is None:
        raise AppError("USER_NOT_FOUND", "Usuari inexistent")
    return user


def _staff_account(account_id):
    account = Account.objects.filter(id=account_id).first()
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Compte inexistent")
    return account


def staff_user_response(user):
    # Data minimisation: no birthdate or gender, which the back office never needs.
    return {
        "id": user.id,
        "dni": user.dni,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "active": user.is_active,
    }


def staff_account_response(account):
    return {
        "id": account.id,
        "iban": account.iban,
        "name": account.name,
        "bank": account.bank,
        "balance": float(account.balance),
        "currency": account.currency,
    }


class StaffView(PolicyEnforcedView):
    authentication_classes = [KofreTokenAuthentication]


class AdminUserListView(StaffView):
    resource_type = "staff-users"
    actions = {"GET": "list-users", "POST": "create-user"}

    def get(self, request):
        return Response([staff_user_response(u) for u in User.objects.order_by("name", "id")])

    def post(self, request):
        return Response(admin_services.create_user(request.data), status=201)


class AdminUserDetailView(StaffView):
    resource_type = "staff-user"
    actions = {
        "PATCH": "set-status",
        "POST": "reset-password",
        "DELETE": "delete-user",
    }

    def patch(self, request, user_id):
        if "active" in request.data and not isinstance(request.data["active"], bool):
            raise AppError("MISSING_FIELDS", "Cal informar 'active' (true o false)")
        with transaction.atomic():
            user = _staff_user(user_id)
            updated = admin_services.update_user(request.user, user.id, request.data)
        return Response(updated)

    def post(self, request, user_id):
        return Response(admin_services.reset_password(
            request.user, user_id, request.data.get("newPassword", "")
        ))

    def delete(self, request, user_id):
        admin_services.delete_user(request.user, user_id)
        return Response(status=204)


class AdminUserAccountsView(StaffView):
    resource_type = "staff-user"
    actions = {"GET": "list-accounts"}

    def get(self, request, user_id):
        _staff_user(user_id)
        accounts = Account.objects.filter(user_id=user_id).order_by("name", "id")
        return Response({"accounts": [staff_account_response(a) for a in accounts]})


class AdminAccountTransfersView(StaffView):
    resource_type = "staff-account"
    actions = {"GET": "list-transfers"}

    def get(self, request, user_id, account_id):
        account = _staff_account(account_id)
        if account.user_id != user_id:
            raise AppError("ACCOUNT_NOT_FOUND", "Compte inexistent")
        return Response(payments_for_account(account.iban))

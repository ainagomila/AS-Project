"""Back-office endpoints for administrators and auditors.

Who may call what is decided by the XACML policy (authz/policies), not here:
administrators list users and enable or disable customers; auditors read
accounts and transfers, pseudonymised by the policy's masking obligation.

Users and accounts are addressed by their internal ids, never by DNI or IBAN,
so personal identifiers stay out of URLs and server logs.
"""

from rest_framework.response import Response

from banking.models import Account
from common.errors import AppError
from payments.services import payments_for_account

from . import services
from .authentication import KofreTokenAuthentication
from .models import User
from authz.pep import PolicyEnforcedView


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
    actions = {"GET": "list-users"}

    def get(self, request):
        return Response([staff_user_response(u) for u in User.objects.order_by("name", "id")])


class AdminUserDetailView(StaffView):
    resource_type = "staff-user"
    actions = {"PATCH": "set-status"}

    def patch(self, request, user_id):
        user = User.objects.get(id=user_id)  # existence is checked by the policy
        active = request.data.get("active")
        if not isinstance(active, bool):
            raise AppError("MISSING_FIELDS", "Cal informar 'active' (true o false)")
        user.is_active = active
        user.save(update_fields=["is_active"])
        if not active:
            services.revoke_tokens(user)
        return Response(staff_user_response(user))


class AdminUserAccountsView(StaffView):
    resource_type = "staff-user"
    actions = {"GET": "list-accounts"}

    def get(self, request, user_id):
        accounts = Account.objects.filter(user_id=user_id).order_by("name", "id")
        return Response({"accounts": [staff_account_response(a) for a in accounts]})


class AdminAccountTransfersView(StaffView):
    resource_type = "staff-account"
    actions = {"GET": "list-transfers"}

    def get(self, request, user_id, account_id):
        account = Account.objects.get(id=account_id)  # ownership is checked by the policy
        return Response(payments_for_account(account.iban))

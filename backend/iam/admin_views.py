"""Administrator endpoints.

Authorization is centralised in `iam.permissions`: every view declares the
roles that may call it through `permission_classes` (or `get_permissions` for
the one mixed GET/POST route). Views stay thin and delegate to `admin_services`.
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from common.http import text

from . import admin_services
from .authentication import AnyTokenAuthentication
from .models import Role
from .permissions import IsAdmin, IsAdminOrAuditor


class AdminView(APIView):
    authentication_classes = [AnyTokenAuthentication]


class AdminReadView(AdminView):
    permission_classes = [IsAdminOrAuditor]


class AdminWriteView(AdminView):
    permission_classes = [IsAdmin]


# ---------------------------------------------------------------- users

class AdminUsersView(AdminView):
    def get_permissions(self):
        if self.request.method.upper() == "POST":
            return [IsAdmin()]
        return [IsAdminOrAuditor()]

    def get(self, request):
        return Response(admin_services.list_users())

    def post(self, request):
        body = admin_services.create_user(
            request.user,
            name=text(request, "name"),
            dni=text(request, "dni"),
            email=text(request, "email"),
            phone=text(request, "phone"),
            password=text(request, "password"),
            birthdate=text(request, "birthdate"),
            gender=text(request, "gender"),
            pin=text(request, "pin"),
            role=request.data.get("role") or Role.USER,
            active=request.data.get("active", True),
        )
        return Response(body, status=201)


class AdminUserDetailView(AdminView):
    def get_permissions(self):
        if self.request.method.upper() in ("PATCH", "DELETE", "POST"):
            return [IsAdmin()]
        return [IsAdminOrAuditor()]

    def get(self, request, dni):
        return Response(admin_services.admin_user_response(admin_services._target_user(dni)))

    def patch(self, request, dni):
        return Response(admin_services.update_user(request.user, dni, request.data))

    def delete(self, request, dni):
        admin_services.delete_user(request.user, dni)
        return Response(status=204)


class AdminUserResetPasswordView(AdminWriteView):
    def post(self, request, dni):
        return Response(
            admin_services.reset_user_password(request.user, dni, text(request, "newPassword"))
        )


# ---------------------------------------------------------------- accounts

class AdminUserAccountsView(AdminReadView):
    def get(self, request, dni):
        return Response(admin_services.list_user_accounts(dni))


class AdminAccountsView(AdminReadView):
    def get(self, request):
        return Response(admin_services.list_all_accounts())


class AdminAccountDetailView(AdminWriteView):
    def patch(self, request, iban):
        return Response(admin_services.set_account_status(request.user, iban, text(request, "status")))


# ---------------------------------------------------------------- cards

class AdminUserCardsView(AdminReadView):
    def get(self, request, dni):
        return Response(admin_services.list_user_cards(dni))


class AdminCardsView(AdminReadView):
    def get(self, request):
        return Response(admin_services.list_all_cards())


class AdminCardDetailView(AdminWriteView):
    def patch(self, request, pan):
        return Response(admin_services.set_card_status(request.user, pan, text(request, "status")))

    def delete(self, request, pan):
        admin_services.delete_card(request.user, pan)
        return Response(status=204)


# ---------------------------------------------------------------- transfers

class AdminAccountTransfersView(AdminReadView):
    def get(self, request, dni, iban):
        return Response(admin_services.list_account_transfers(dni, iban))


class AdminTransfersView(AdminReadView):
    def get(self, request):
        return Response(admin_services.list_all_transfers())


# ---------------------------------------------------------------- audit + settings + stats

class AdminAuditLogsView(AdminReadView):
    def get(self, request):
        return Response(admin_services.list_audit_logs())


class AdminSettingsView(AdminReadView):
    def get(self, request):
        return Response(admin_services.list_settings())


class AdminSettingDetailView(AdminWriteView):
    def patch(self, request, key):
        return Response(admin_services.update_setting(request.user, key, request.data.get("value")))


class AdminStatsView(AdminReadView):
    def get(self, request):
        return Response(admin_services.stats())

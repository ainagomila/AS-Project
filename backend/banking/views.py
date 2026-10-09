from rest_framework.response import Response

from common.http import text
from iam.views import AuthenticatedView

from . import services


class AccountListView(AuthenticatedView):
    def get(self, request, dni):
        return Response(services.list_accounts(dni))

    def post(self, request, dni):
        body = services.add_account(
            dni,
            text(request, "iban"),
            text(request, "name"),
            text(request, "bank"),
            request.data.get("balance"),
            text(request, "currency"),
        )
        return Response(body, status=201)


class AccountDetailView(AuthenticatedView):
    def get(self, request, dni, iban):
        return Response(services.get_account(dni, iban))

    def patch(self, request, dni, iban):
        return Response(services.rename_account(dni, iban, text(request, "name")))

    def delete(self, request, dni, iban):
        services.delete_account(dni, iban, text(request, "pin"))
        return Response(status=204)

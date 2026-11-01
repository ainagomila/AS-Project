from rest_framework.response import Response

from common.http import text
from common.validators import has_text
from iam.views import AuthenticatedView

from . import card_services, services


class AccountListView(AuthenticatedView):
    resource_type = "user"
    actions = {"GET": "list-accounts", "POST": "create-account"}

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
    resource_type = "account"
    actions = {"GET": "read", "PATCH": "rename", "DELETE": "delete"}

    def get(self, request, dni, iban):
        return Response(services.get_account(dni, iban))

    def patch(self, request, dni, iban):
        return Response(services.rename_account(dni, iban, text(request, "name")))

    def delete(self, request, dni, iban):
        services.delete_account(dni, iban, text(request, "pin"))
        return Response(status=204)


class UserCardsView(AuthenticatedView):
    resource_type = "user"
    actions = {"GET": "list-cards"}

    def get(self, request, dni):
        return Response(card_services.list_user_cards(dni))


class AccountCardsView(AuthenticatedView):
    resource_type = "account"
    actions = {"GET": "list-cards", "POST": "create-card"}

    def get(self, request, dni, iban):
        return Response(card_services.list_account_cards(dni, iban))

    def post(self, request, dni, iban):
        body = card_services.add_card(
            dni,
            iban,
            text(request, "pan"),
            text(request, "expireDate"),
            text(request, "alias"),
            text(request, "cvv"),
            text(request, "pin"),
            text(request, "type"),
            text(request, "bank"),
        )
        return Response(body, status=201)


class CardDetailView(AuthenticatedView):
    resource_type = "card"
    actions = {"GET": "read", "PATCH": "update", "DELETE": "delete"}

    def get(self, request, dni, iban, pan):
        return Response(card_services.get_card(dni, pan))

    def patch(self, request, dni, iban, pan):
        alias, status = text(request, "alias"), text(request, "status")
        result = None
        if has_text(alias):
            result = card_services.update_alias(dni, iban, pan, alias)
        if has_text(status):
            result = card_services.update_status(dni, iban, pan, status)
        # With neither field the original answers 200 with an empty body.
        return Response(result)

    def delete(self, request, dni, iban, pan):
        card_services.delete_card(dni, iban, pan, text(request, "pin"))
        return Response(status=204)


class VerifyCardView(AuthenticatedView):
    resource_type = "card"
    actions = {"POST": "verify-card"}

    def post(self, request, dni, iban, pan):
        return Response(card_services.verify_card(dni, iban, pan, text(request, "pin")))

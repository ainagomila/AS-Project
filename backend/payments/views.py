from rest_framework.response import Response

from common.http import text
from iam.views import AuthenticatedView

from . import services


class TransfersView(AuthenticatedView):
    def get(self, request, dni, iban):
        params = request.query_params
        return Response(
            services.list_transfers(
                dni,
                iban,
                q=params.get("q"),
                only_expenses=(params.get("onlyExpenses") or "").lower() in ("true", "1", "yes", "on"),
                date_from=params.get("from"),
                date_to=params.get("to"),
                sort=params.get("sort"),
            )
        )

    def post(self, request, dni, iban):
        services.add_transfer(
            dni,
            iban,
            text(request, "beneficiary"),
            text(request, "destinationIban"),
            request.data.get("amount"),
            text(request, "currency"),
            text(request, "concept"),
            text(request, "pin"),
            request.data.get("categories"),
        )
        return Response(status=200)

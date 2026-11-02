"""Policy enforcement point.

Every API view extends PolicyEnforcedView and names its resource type and the
action each HTTP method performs. After authentication, the view asks the PDP
for a decision and only runs on Permit. NotApplicable, Indeterminate and any
obligation the PEP cannot fulfil are treated as Deny (deny-biased PEP).
"""

import logging

from rest_framework.views import APIView

from common.errors import AppError

from . import obligations, pdp, pip
from .models import AuditEvent
from .xacml import DENY, PERMIT

log = logging.getLogger("kofre.authz")

ERROR_ADVICE = "urn:kofre:advice:error"
CONCEAL_ADVICE = "urn:kofre:advice:conceal-existence"
ADVICE_CODE = "urn:kofre:advice:code"
ADVICE_MESSAGE = "urn:kofre:advice:message"

# What a concealed resource looks like: the same answer as a missing one.
NOT_FOUND = {
    "account": ("ACCOUNT_NOT_FOUND", "Compte inexistent"),
    "card": ("CARD_NOT_FOUND", "Targeta inexistent"),
    "staff-user": ("USER_NOT_FOUND", "Usuari inexistent"),
    "staff-account": ("ACCOUNT_NOT_FOUND", "Compte inexistent"),
}


class Decision:
    def __init__(self, request, resource_type, action, result):
        self.request = request
        self.resource_type = resource_type
        self.action = action
        self.result = result

    @property
    def permitted(self):
        return self.result.decision == PERMIT

    @property
    def obligations(self):
        return self.result.obligations

    def advice(self, advice_id):
        return next((a for a in self.result.advice if a["id"] == advice_id), None)


def _first(attributes, key, default=""):
    values = attributes.get(key, [])
    return values[0] if values else default


def _deny_error(decision):
    if decision.advice(CONCEAL_ADVICE) is not None and decision.resource_type in NOT_FOUND:
        return AppError(*NOT_FOUND[decision.resource_type])
    error = decision.advice(ERROR_ADVICE)
    if error is not None:
        attributes = error["attributes"]
        return AppError(_first(attributes, ADVICE_CODE, "FORBIDDEN"), _first(attributes, ADVICE_MESSAGE, "Accés denegat"))
    return AppError("FORBIDDEN", "Accés denegat")


class PolicyEnforcedView(APIView):
    resource_type = None  # must be set by every view
    actions = {}  # HTTP method -> action id

    def initial(self, request, *args, **kwargs):
        self.authz = None
        super().initial(request, *args, **kwargs)  # authentication happens here
        if not hasattr(self, request.method.lower()):
            return  # dispatch answers 405 without running anything
        self.authz = self._decide(request, kwargs)
        try:
            obligations.check_supported(self.authz.obligations)
        except obligations.UnfulfillableObligation as exc:
            log.error("Denied: cannot fulfil obligation %s", exc)
            raise AppError("FORBIDDEN", "Accés denegat") from None
        if not self.authz.permitted:
            raise _deny_error(self.authz)

    def _decide(self, request, kwargs):
        action = self.actions.get(request.method)
        if self.resource_type is None or action is None:
            # A view nobody described is never reachable.
            log.error("%s has no resource type or no action for %s", type(self).__name__, request.method)
            raise AppError("FORBIDDEN", "Accés denegat")
        attributes = pip.build_request(request, self.resource_type, action, kwargs)
        result = pdp.decide(attributes)
        log.info("%s %s on %s -> %s (%s)", _first(attributes, pip.SUBJECT_ROLE), action,
                 self.resource_type, result.decision, result.by or "no rule")
        decision = Decision(request, self.resource_type, action, result)
        decision.attributes = attributes
        return decision

    def finalize_response(self, request, response, *args, **kwargs):
        decision = getattr(self, "authz", None)
        if decision is not None:
            if decision.permitted and 200 <= response.status_code < 300 and response.data is not None:
                fields = obligations.fields_to_mask(decision.obligations)
                if fields:
                    response.data = obligations.mask(response.data, fields)
            # Denials the policy did not reach a Deny for (NotApplicable,
            # Indeterminate) are security events too, so they are always recorded.
            unexpected = decision.result.decision not in (PERMIT, DENY)
            if unexpected or any(o["id"] == obligations.AUDIT for o in decision.obligations):
                _audit(decision, response.status_code)
        return super().finalize_response(request, response, *args, **kwargs)


def _audit(decision, status_code):
    attributes = decision.attributes
    AuditEvent.objects.create(
        subject_id=_first(attributes, pip.SUBJECT_ID),
        subject_role=_first(attributes, pip.SUBJECT_ROLE),
        action=decision.action,
        resource_type=decision.resource_type,
        resource_id=_first(attributes, pip.RESOURCE_ID),
        decision=decision.result.decision if decision.result.decision in (PERMIT, DENY) else DENY,
        rule=decision.result.by or "",
        status_code=status_code,
        client_ip=_first(attributes, pip.CLIENT_IP),
    )

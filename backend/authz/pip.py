"""Policy information point: builds the XACML request for an API call.

Subject attributes come from the authenticated user and their OAuth token,
resource attributes from the URL and the database, action from the view.
"""

from datetime import datetime, timezone

from banking.models import Account, Card
from iam.models import User

from .xacml import ACTION, ENVIRONMENT, RESOURCE, SUBJECT

SUBJECT_ID = (SUBJECT, "urn:oasis:names:tc:xacml:1.0:subject:subject-id")
SUBJECT_DNI = (SUBJECT, "urn:kofre:subject:dni")
SUBJECT_ROLE = (SUBJECT, "urn:oasis:names:tc:xacml:2.0:subject:role")
SUBJECT_AUTHENTICATED = (SUBJECT, "urn:kofre:subject:authenticated")
SUBJECT_ACTIVE = (SUBJECT, "urn:kofre:subject:active")
SUBJECT_SCOPE = (SUBJECT, "urn:kofre:subject:scope")

RESOURCE_TYPE = (RESOURCE, "urn:kofre:resource:type")
RESOURCE_ID = (RESOURCE, "urn:oasis:names:tc:xacml:1.0:resource:resource-id")
PATH_DNI = (RESOURCE, "urn:kofre:resource:path-dni")
PATH_IBAN = (RESOURCE, "urn:kofre:resource:path-iban")
OWNER_ID = (RESOURCE, "urn:kofre:resource:owner-id")
ACCOUNT_IBAN = (RESOURCE, "urn:kofre:resource:account-iban")
EXISTS = (RESOURCE, "urn:kofre:resource:exists")
TARGET_USER_ID = (RESOURCE, "urn:kofre:resource:target-user-id")
TARGET_ROLE = (RESOURCE, "urn:kofre:resource:target-role")

ACTION_ID = (ACTION, "urn:oasis:names:tc:xacml:1.0:action:action-id")

CURRENT_DATETIME = (ENVIRONMENT, "urn:oasis:names:tc:xacml:1.0:environment:current-dateTime")
CLIENT_IP = (ENVIRONMENT, "urn:kofre:environment:client-ip")


def subject_attributes(user, token):
    if user is None:
        return {SUBJECT_AUTHENTICATED: [False], SUBJECT_ACTIVE: [False], SUBJECT_ROLE: ["anonymous"]}
    scopes = (getattr(token, "scope", "") or "").split()
    return {
        SUBJECT_AUTHENTICATED: [True],
        SUBJECT_ID: [user.id],
        SUBJECT_DNI: [user.dni],
        SUBJECT_ROLE: [user.role],
        SUBJECT_ACTIVE: [user.is_active],
        SUBJECT_SCOPE: scopes,
    }


def _account_attributes(iban):
    account = Account.objects.filter(iban=iban).first()
    if account is None:
        return {}
    return {OWNER_ID: [account.user_id], RESOURCE_ID: [account.id]}


def _card_attributes(pan):
    card = Card.objects.find_by_pan(pan)
    if card is None:
        return {}
    account = Account.objects.filter(id=card.account_id).first()
    if account is None:
        return {RESOURCE_ID: [card.id]}
    return {OWNER_ID: [account.user_id], ACCOUNT_IBAN: [account.iban], RESOURCE_ID: [card.id]}


def _target_user_attributes(user_id):
    target = User.objects.filter(id=user_id).first()
    if target is None:
        return None, {EXISTS: [False]}
    return target, {
        EXISTS: [True],
        TARGET_USER_ID: [target.id],
        TARGET_ROLE: [target.role],
        RESOURCE_ID: [target.id],
    }


def resource_attributes(resource_type, kwargs):
    """Attributes of the resource a view acts on. The resource types are the
    ones the policy knows; an unknown type simply matches no policy."""
    attributes = {RESOURCE_TYPE: [resource_type]}
    if "dni" in kwargs:
        attributes[PATH_DNI] = [kwargs["dni"]]
    if "iban" in kwargs:
        attributes[PATH_IBAN] = [kwargs["iban"]]

    if resource_type == "account":
        attributes.update(_account_attributes(kwargs["iban"]))
    elif resource_type == "card":
        attributes.update(_card_attributes(kwargs["pan"]))
    elif resource_type in ("staff-users", "audit-log"):
        attributes[EXISTS] = [True]
    elif resource_type == "staff-user":
        _, found = _target_user_attributes(kwargs["user_id"])
        attributes.update(found)
    elif resource_type == "staff-account":
        target, found = _target_user_attributes(kwargs["user_id"])
        attributes.update(found)
        account = Account.objects.filter(id=kwargs["account_id"]).first()
        # The account must exist and belong to the user named in the URL.
        if target is None or account is None or account.user_id != target.id:
            attributes[EXISTS] = [False]
        else:
            attributes[RESOURCE_ID] = [account.id]
    return attributes


def environment_attributes(request):
    return {
        CURRENT_DATETIME: [datetime.now(timezone.utc).isoformat()],
        CLIENT_IP: [request.META.get("REMOTE_ADDR", "")],
    }


def build_request(request, resource_type, action, kwargs):
    attributes = {}
    attributes.update(subject_attributes(request.user, request.auth))
    attributes.update(resource_attributes(resource_type, kwargs))
    attributes[ACTION_ID] = [action]
    attributes.update(environment_attributes(request))
    return attributes

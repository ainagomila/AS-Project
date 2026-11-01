from rest_framework.response import Response

from iam.authentication import KofreTokenAuthentication

from .models import AuditEvent
from .pep import PolicyEnforcedView

AUDIT_PAGE = 200


def audit_event_response(event):
    return {
        "at": event.created_at.isoformat(),
        "subjectId": event.subject_id,
        "subjectRole": event.subject_role,
        "action": event.action,
        "resourceType": event.resource_type,
        "resourceId": event.resource_id,
        "decision": event.decision,
        "rule": event.rule,
        "status": event.status_code,
    }


class AuditLogView(PolicyEnforcedView):
    authentication_classes = [KofreTokenAuthentication]
    resource_type = "audit-log"
    actions = {"GET": "read"}

    def get(self, request):
        events = AuditEvent.objects.all()[:AUDIT_PAGE]
        return Response({"events": [audit_event_response(e) for e in events]})

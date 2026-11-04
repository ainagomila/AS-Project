"""Security event log: one JSON line per event on stdout (the container runtime keeps it).

Events name users by their internal id only. DNIs, passwords, PINs and card
numbers are never passed in, so a failed login for an unknown DNI logs just the
client IP. Each line goes through json.dumps, which escapes newlines and control
characters, so user input cannot forge extra log lines.
"""

import json
import logging
from datetime import datetime, timezone

log = logging.getLogger("kofre.security")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def security_event(event, request, level=logging.INFO, **fields):
    """Log a security event. Pass identifiers as internal ids, never as DNI or IBAN."""
    fields = {"event": event, "ip": request.META.get("REMOTE_ADDR", ""), **fields}
    log.log(level, event, extra={"fields": fields})

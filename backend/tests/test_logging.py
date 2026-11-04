import json
import logging

import pytest
from django.test import Client

from common.seclog import JsonFormatter
from iam.models import User

from .conftest import DNI_A, PASSWORD, PIN

pytestmark = pytest.mark.django_db


def _events(caplog):
    return [r.fields for r in caplog.records if r.name == "kofre.security"]


def _lines(caplog):
    formatter = JsonFormatter()
    return [formatter.format(r) for r in caplog.records if r.name.startswith("kofre")]


def test_logins_wrong_pins_and_lockouts_are_logged_without_personal_data(ana, caplog):
    caplog.set_level(logging.INFO, logger="kofre")
    user_id = User.objects.get_by_natural_key(DNI_A).id
    browser = Client()
    for _ in range(5):
        browser.post("/accounts/login/", {"username": DNI_A, "password": "Wrong_123"})
    Client(REMOTE_ADDR="10.0.0.2").post("/accounts/login/", {"username": DNI_A, "password": PASSWORD})
    ana.client.post(ana.url("/security/verify-pin"), {"pin": "000000"}, format="json")

    events = _events(caplog)
    assert [e["event"] for e in events] == ["login.failure"] * 5 + ["lockout", "login.success", "pin.failure"]
    assert events[5] == {"event": "lockout", "ip": "127.0.0.1", "after": "login.failure", "minutes": 15}
    assert events[6] == {"event": "login.success", "ip": "10.0.0.2", "user_id": user_id}
    assert events[7]["user_id"] == user_id

    output = "\n".join(_lines(caplog))
    for secret in (DNI_A, PASSWORD, "Wrong_123", PIN, "000000"):
        assert secret not in output


def test_log_lines_are_single_line_json_in_utc():
    record = logging.LogRecord("kofre.security", logging.WARNING, __file__, 1, "login.failure", None, None)
    record.fields = {"event": "login.failure", "ip": "1.2.3.4\nFAKE ENTRY"}
    line = JsonFormatter().format(record)
    assert "\n" not in line
    entry = json.loads(line)
    assert entry["ts"].endswith("+00:00")
    assert (entry["level"], entry["event"], entry["ip"]) == ("WARNING", "login.failure", "1.2.3.4\nFAKE ENTRY")

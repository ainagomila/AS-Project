"""Policy decision point: the loaded policy and the decide() entry point."""

from functools import lru_cache
from pathlib import Path

from django.conf import settings

from . import xacml

DEFAULT_POLICY = Path(__file__).resolve().parent / "policies" / "kofre-policy.xml"


def policy_path():
    return Path(getattr(settings, "AUTHZ_POLICY_FILE", "") or DEFAULT_POLICY)


@lru_cache(maxsize=1)
def policy():
    """The policy, parsed once. An unsupported policy stops the server from starting."""
    return xacml.load(policy_path().read_text(encoding="utf-8"))


def decide(request_attributes):
    return xacml.evaluate(policy(), request_attributes)

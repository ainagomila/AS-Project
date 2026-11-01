"""The XACML engine, the policy file and the enforcement point."""

import pytest
from django.urls import URLPattern, URLResolver, get_resolver

from authz import obligations, pdp, pip, xacml
from authz.pep import PolicyEnforcedView

NS = 'xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17"'
STRING = "http://www.w3.org/2001/XMLSchema#string"
ROLE = '<AttributeDesignator Category="urn:oasis:names:tc:xacml:1.0:subject-category:access-subject" ' \
       f'AttributeId="role" DataType="{STRING}" MustBePresent="false"/>'


def role_rule(rule_id, effect, role, obligation=""):
    return f"""
    <Rule RuleId="{rule_id}" Effect="{effect}">
      <Target><AnyOf><AllOf>
        <Match MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
          <AttributeValue DataType="{STRING}">{role}</AttributeValue>{ROLE}
        </Match>
      </AllOf></AnyOf></Target>{obligation}
    </Rule>"""


def policy(algorithm, *rules):
    return xacml.load(f"""
    <Policy {NS} PolicyId="p" RuleCombiningAlgId="urn:oasis:names:tc:xacml:3.0:rule-combining-algorithm:{algorithm}">
      {''.join(rules)}
    </Policy>""")


def ask(loaded, *roles):
    return xacml.evaluate(loaded, {(xacml.SUBJECT, "role"): list(roles)})


# ------------------------------------------------------------------ engine

def test_combining_algorithms():
    permit_a = role_rule("permit-a", "Permit", "a")
    deny_a = role_rule("deny-a", "Deny", "a")

    deny_overrides = policy("deny-overrides", permit_a, deny_a)
    assert (ask(deny_overrides, "a").decision, ask(deny_overrides, "a").by) == ("Deny", "deny-a")
    assert ask(deny_overrides, "b").decision == "NotApplicable"

    permit_overrides = policy("permit-overrides", deny_a, permit_a)
    assert ask(permit_overrides, "a").decision == "Permit"

    first = xacml.load(f"""
    <Policy {NS} PolicyId="p" RuleCombiningAlgId="urn:oasis:names:tc:xacml:1.0:rule-combining-algorithm:first-applicable">
      {permit_a}{deny_a}
    </Policy>""")
    assert ask(first, "a").by == "permit-a"

    unless = policy("deny-unless-permit", permit_a)
    assert ask(unless, "b").decision == "Deny"


def test_obligations_follow_the_decision():
    audit = """<ObligationExpressions>
        <ObligationExpression ObligationId="audit" FulfillOn="Permit"/>
      </ObligationExpressions>"""
    loaded = policy("deny-overrides", role_rule("permit-a", "Permit", "a", audit))
    assert [o["id"] for o in ask(loaded, "a").obligations] == ["audit"]
    assert ask(loaded, "b").obligations == []


def test_missing_mandatory_attribute_is_indeterminate():
    loaded = xacml.load(f"""
    <Policy {NS} PolicyId="p" RuleCombiningAlgId="urn:oasis:names:tc:xacml:3.0:rule-combining-algorithm:deny-overrides">
      <Rule RuleId="r" Effect="Permit">
        <Condition>
          <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-is-in">
            <AttributeValue DataType="{STRING}">x</AttributeValue>
            <AttributeDesignator Category="c" AttributeId="needed" DataType="{STRING}" MustBePresent="true"/>
          </Apply>
        </Condition>
      </Rule>
    </Policy>""")
    assert xacml.evaluate(loaded, {}).decision == "Indeterminate"


@pytest.mark.parametrize(
    "document",
    [
        f'<!DOCTYPE x [<!ENTITY a "b">]><Policy {NS} PolicyId="p" '
        'RuleCombiningAlgId="urn:oasis:names:tc:xacml:3.0:rule-combining-algorithm:deny-overrides"/>',
        f'<Policy {NS} PolicyId="p" RuleCombiningAlgId="urn:example:only-one-applicable"/>',
        f'<Policy {NS} PolicyId="p" RuleCombiningAlgId="urn:oasis:names:tc:xacml:3.0:rule-combining-algorithm:deny-overrides">'
        '<VariableDefinition VariableId="v"/></Policy>',
        f'<Policy {NS} PolicyId="p" RuleCombiningAlgId="urn:oasis:names:tc:xacml:3.0:rule-combining-algorithm:deny-overrides">'
        '<Rule RuleId="r" Effect="Permit"><Condition>'
        '<Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-regexp-match"/>'
        '</Condition></Rule></Policy>',
        '<Policy PolicyId="p" RuleCombiningAlgId="x"/>',
        "<not-xml",
    ],
)
def test_unsupported_policies_are_rejected_at_load(document):
    with pytest.raises(xacml.PolicyError):
        xacml.load(document)


def test_the_project_policy_loads():
    assert pdp.policy().id == "urn:kofre:policyset:root"


def test_unknown_resource_type_is_not_applicable():
    request = {
        **pip.subject_attributes(None, None),
        pip.RESOURCE_TYPE: ["something-new"],
        pip.ACTION_ID: ["read"],
    }
    assert pdp.decide(request).decision == "NotApplicable"


# ------------------------------------------------------------------ obligations

def test_unknown_obligations_cannot_be_fulfilled():
    with pytest.raises(obligations.UnfulfillableObligation):
        obligations.check_supported([{"id": "urn:example:send-email", "attributes": {}}])
    with pytest.raises(obligations.UnfulfillableObligation):
        obligations.check_supported([{"id": obligations.MASK, "attributes": {obligations.MASK_FIELD: ["salary"]}}])


def test_masking():
    data = [{"dni": "12345678Z", "name": "Ana Blanco Ruiz", "phone": "+34600123456",
             "accounts": [{"iban": "ES9121000418450200051332", "balance": 5}]}]
    masked = obligations.mask(data, {"dni", "name", "phone", "iban"})
    assert masked == [{"dni": "*****678Z", "name": "A. B. R.", "phone": "+34 *** *** 456",
                       "accounts": [{"iban": "ES91 **** **** 1332", "balance": 5}]}]


# ------------------------------------------------------------------ enforcement coverage

def _api_views(patterns, prefix=""):
    for entry in patterns:
        if isinstance(entry, URLResolver):
            if entry.namespace == "oauth2_provider":
                continue  # the OAuth endpoints protect themselves
            yield from _api_views(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern) and hasattr(entry.callback, "view_class"):
            if str(entry.pattern) == "accounts/login/":
                continue  # the OAuth login page is a Django form, not an API view
            yield prefix + str(entry.pattern), entry.callback.view_class


def test_every_api_route_goes_through_the_policy():
    """A new endpoint without a resource type and actions would fail here."""
    checked = 0
    for route, view in _api_views(get_resolver().url_patterns):
        if not view.__module__.split(".")[0] in ("iam", "banking", "payments", "authz"):
            continue
        assert issubclass(view, PolicyEnforcedView), route
        assert view.resource_type, route
        methods = {m.upper() for m in ("get", "post", "patch", "put", "delete") if hasattr(view, m)}
        assert methods <= set(view.actions), (route, methods - set(view.actions))
        checked += 1
    assert checked == 18  # update when adding an endpoint

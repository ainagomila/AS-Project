"""A small XACML 3.0 policy engine.

It loads a subset of XACML 3.0 XML (PolicySet, Policy, Rule, Target, Condition,
ObligationExpressions and AdviceExpressions) and evaluates requests against it.
Any element, function, data type or combining algorithm outside that subset is
rejected when the policy is loaded, so a policy the engine does not fully
understand never goes live.

Requests are dictionaries ``{(category, attribute_id): [values]}``: every
attribute is a bag, as in XACML.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

NS = "urn:oasis:names:tc:xacml:3.0:core:schema:wd-17"

PERMIT = "Permit"
DENY = "Deny"
NOT_APPLICABLE = "NotApplicable"
INDETERMINATE = "Indeterminate"

SUBJECT = "urn:oasis:names:tc:xacml:1.0:subject-category:access-subject"
RESOURCE = "urn:oasis:names:tc:xacml:3.0:attribute-category:resource"
ACTION = "urn:oasis:names:tc:xacml:3.0:attribute-category:action"
ENVIRONMENT = "urn:oasis:names:tc:xacml:3.0:attribute-category:environment"

XS = "http://www.w3.org/2001/XMLSchema#"
STRING, BOOLEAN, INTEGER = XS + "string", XS + "boolean", XS + "integer"

F1 = "urn:oasis:names:tc:xacml:1.0:function:"


class PolicyError(Exception):
    """The policy file uses something this engine does not support."""


class EvaluationError(Exception):
    """A request could not be evaluated (XACML 'Indeterminate')."""


def _tag(element):
    return element.tag.removeprefix("{" + NS + "}")


def _children(element, name=None):
    return [c for c in element if name is None or _tag(c) == name]


def _required(element, attribute):
    value = element.get(attribute)
    if not value:
        raise PolicyError(f"<{_tag(element)}> needs a {attribute} attribute")
    return value


# ----------------------------------------------------------------- data types

def _parse_value(data_type, text):
    text = (text or "").strip()
    if data_type == STRING:
        return text
    if data_type == BOOLEAN:
        if text not in ("true", "false"):
            raise PolicyError(f"Not a boolean: {text!r}")
        return text == "true"
    if data_type == INTEGER:
        try:
            return int(text)
        except ValueError:
            raise PolicyError(f"Not an integer: {text!r}") from None
    raise PolicyError(f"Unsupported data type {data_type}")


# ----------------------------------------------------------------- functions

def _one_and_only(bag):
    if not isinstance(bag, list) or len(bag) != 1:
        raise EvaluationError(f"one-and-only expects a bag with one value, got {bag!r}")
    return bag[0]


def _equal(a, b):
    if isinstance(a, list) or isinstance(b, list):
        raise EvaluationError("equality functions take single values, not bags")
    return a == b


def _is_in(value, bag):
    if not isinstance(bag, list):
        raise EvaluationError("is-in expects a bag as its second argument")
    return value in bag


def _bag_size(bag):
    if not isinstance(bag, list):
        raise EvaluationError("bag-size expects a bag")
    return len(bag)


def _boolean(value):
    if not isinstance(value, bool):
        raise EvaluationError(f"expected a boolean, got {value!r}")
    return value


FUNCTIONS = {
    F1 + "string-equal": (2, _equal),
    F1 + "boolean-equal": (2, _equal),
    F1 + "integer-equal": (2, _equal),
    F1 + "string-one-and-only": (1, _one_and_only),
    F1 + "boolean-one-and-only": (1, _one_and_only),
    F1 + "string-is-in": (2, _is_in),
    F1 + "string-bag-size": (1, _bag_size),
    F1 + "not": (1, lambda v: not _boolean(v)),
    F1 + "and": (None, lambda *vs: all(_boolean(v) for v in vs)),
    F1 + "or": (None, lambda *vs: any(_boolean(v) for v in vs)),
}

# Match functions compare an AttributeValue with one value of a bag.
MATCH_FUNCTIONS = {F1 + "string-equal", F1 + "boolean-equal", F1 + "integer-equal"}


# ----------------------------------------------------------------- expressions

@dataclass
class Value:
    value: object

    def evaluate(self, request):
        return self.value


@dataclass
class Designator:
    category: str
    attribute_id: str
    data_type: str
    must_be_present: bool

    def evaluate(self, request):
        bag = list(request.get((self.category, self.attribute_id), []))
        if self.must_be_present and not bag:
            raise EvaluationError(f"missing attribute {self.attribute_id}")
        return bag


@dataclass
class Apply:
    function_id: str
    arguments: list

    def evaluate(self, request):
        _, function = FUNCTIONS[self.function_id]
        return function(*(a.evaluate(request) for a in self.arguments))


def _parse_expression(element):
    name = _tag(element)
    if name == "AttributeValue":
        data_type = _required(element, "DataType")
        return Value(_parse_value(data_type, element.text))
    if name == "AttributeDesignator":
        data_type = _required(element, "DataType")
        _parse_value(data_type, "true" if data_type == BOOLEAN else "0")  # checks the type
        return Designator(
            _required(element, "Category"),
            _required(element, "AttributeId"),
            data_type,
            element.get("MustBePresent", "false") == "true",
        )
    if name == "Apply":
        function_id = _required(element, "FunctionId")
        if function_id not in FUNCTIONS:
            raise PolicyError(f"Unsupported function {function_id}")
        arguments = [_parse_expression(c) for c in _children(element) if _tag(c) != "Description"]
        arity, _ = FUNCTIONS[function_id]
        if arity is not None and len(arguments) != arity:
            raise PolicyError(f"{function_id} takes {arity} arguments, got {len(arguments)}")
        return Apply(function_id, arguments)
    raise PolicyError(f"Unsupported expression <{name}>")


# ----------------------------------------------------------------- targets

@dataclass
class Match:
    function_id: str
    value: Value
    designator: Designator

    def matches(self, request):
        _, function = FUNCTIONS[self.function_id]
        return any(function(self.value.value, v) for v in self.designator.evaluate(request))


@dataclass
class Target:
    any_ofs: list  # AND of AnyOf; each AnyOf is an OR of AllOf; each AllOf an AND of Match

    def matches(self, request):
        return all(any(all(m.matches(request) for m in all_of) for all_of in any_of) for any_of in self.any_ofs)


def _parse_target(element):
    if element is None:
        return Target([])
    any_ofs = []
    for any_of in _children(element, "AnyOf"):
        all_ofs = []
        for all_of in _children(any_of, "AllOf"):
            matches = []
            for match in _children(all_of, "Match"):
                function_id = _required(match, "MatchId")
                if function_id not in MATCH_FUNCTIONS:
                    raise PolicyError(f"Unsupported match function {function_id}")
                value = _children(match, "AttributeValue")
                designator = _children(match, "AttributeDesignator")
                if len(value) != 1 or len(designator) != 1:
                    raise PolicyError("<Match> needs one AttributeValue and one AttributeDesignator")
                matches.append(Match(function_id, _parse_expression(value[0]), _parse_expression(designator[0])))
            if not matches:
                raise PolicyError("<AllOf> needs at least one <Match>")
            all_ofs.append(matches)
        if not all_ofs:
            raise PolicyError("<AnyOf> needs at least one <AllOf>")
        any_ofs.append(all_ofs)
    return Target(any_ofs)


# ----------------------------------------------------------------- obligations and advice

@dataclass
class Directive:
    """An obligation or advice expression, attached to one effect."""

    directive_id: str
    effect: str
    assignments: list  # (attribute_id, expression)

    def evaluate(self, request):
        values = {}
        for attribute_id, expression in self.assignments:
            result = expression.evaluate(request)
            values.setdefault(attribute_id, []).extend(result if isinstance(result, list) else [result])
        return {"id": self.directive_id, "attributes": values}


def _parse_directives(element, container, item, id_attribute, effect_attribute):
    found = []
    for wrapper in _children(element, container):
        for expression in _children(wrapper, item):
            effect = _required(expression, effect_attribute)
            if effect not in (PERMIT, DENY):
                raise PolicyError(f"{effect_attribute} must be Permit or Deny")
            assignments = []
            for assignment in _children(expression, "AttributeAssignmentExpression"):
                inner = [c for c in assignment if _tag(c) != "Description"]
                if len(inner) != 1:
                    raise PolicyError("<AttributeAssignmentExpression> needs exactly one expression")
                assignments.append((_required(assignment, "AttributeId"), _parse_expression(inner[0])))
            found.append(Directive(_required(expression, id_attribute), effect, assignments))
    return found


def _obligations(element):
    return _parse_directives(element, "ObligationExpressions", "ObligationExpression", "ObligationId", "FulfillOn")


def _advice(element):
    return _parse_directives(element, "AdviceExpressions", "AdviceExpression", "AdviceId", "AppliesTo")


# ----------------------------------------------------------------- results

@dataclass
class Result:
    decision: str
    by: str = ""  # id of the rule that produced the decision
    obligations: list = field(default_factory=list)
    advice: list = field(default_factory=list)
    reason: str = ""


def _with_directives(result, owner, request):
    """Attach the owner's obligations and advice for the decision it reached."""
    if result.decision not in (PERMIT, DENY):
        return result
    try:
        obligations = [d.evaluate(request) for d in owner.obligations if d.effect == result.decision]
        advice = [d.evaluate(request) for d in owner.advice if d.effect == result.decision]
    except EvaluationError as exc:
        return Result(INDETERMINATE, owner.id, reason=str(exc))
    return Result(result.decision, result.by, obligations + result.obligations, advice + result.advice, result.reason)


# ----------------------------------------------------------------- combining algorithms

def _overrides(winner, loser):
    def combine(children, request):
        results = []
        for child in children:
            result = child.evaluate(request)
            if result.decision == winner:
                found = [result]
                # Collect the obligations of every child that reached the same decision.
                for other in children[len(results) + 1:]:
                    extra = other.evaluate(request)
                    if extra.decision == winner:
                        found.append(extra)
                return Result(
                    winner,
                    result.by,
                    [o for r in found for o in r.obligations],
                    [a for r in found for a in r.advice],
                )
            results.append(result)
        for result in results:
            if result.decision == INDETERMINATE:
                return result
        matched = [r for r in results if r.decision == loser]
        if matched:
            return Result(
                loser,
                matched[0].by,
                [o for r in matched for o in r.obligations],
                [a for r in matched for a in r.advice],
            )
        return Result(NOT_APPLICABLE)

    return combine


def _first_applicable(children, request):
    for child in children:
        result = child.evaluate(request)
        if result.decision != NOT_APPLICABLE:
            return result
    return Result(NOT_APPLICABLE)


def _unless(default, other):
    def combine(children, request):
        found = []
        for child in children:
            result = child.evaluate(request)
            if result.decision == other:
                found.append(result)
        if found:
            return Result(
                other,
                found[0].by,
                [o for r in found for o in r.obligations],
                [a for r in found for a in r.advice],
            )
        return Result(default, "default:" + default.lower())

    return combine


ALGORITHMS = {
    "deny-overrides": _overrides(DENY, PERMIT),
    "permit-overrides": _overrides(PERMIT, DENY),
    "first-applicable": _first_applicable,
    "deny-unless-permit": _unless(DENY, PERMIT),
    "permit-unless-deny": _unless(PERMIT, DENY),
}
ALGORITHM_PREFIXES = (
    "urn:oasis:names:tc:xacml:1.0:rule-combining-algorithm:",
    "urn:oasis:names:tc:xacml:1.0:policy-combining-algorithm:",
    "urn:oasis:names:tc:xacml:3.0:rule-combining-algorithm:",
    "urn:oasis:names:tc:xacml:3.0:policy-combining-algorithm:",
)


def _algorithm(algorithm_id):
    for prefix in ALGORITHM_PREFIXES:
        name = algorithm_id.removeprefix(prefix)
        if name != algorithm_id and name in ALGORITHMS:
            return ALGORITHMS[name]
    raise PolicyError(f"Unsupported combining algorithm {algorithm_id}")


# ----------------------------------------------------------------- policy elements

@dataclass
class Rule:
    id: str
    effect: str
    target: Target
    condition: object
    obligations: list
    advice: list

    def evaluate(self, request):
        try:
            if not self.target.matches(request):
                return Result(NOT_APPLICABLE)
            if self.condition is not None and not _boolean(self.condition.evaluate(request)):
                return Result(NOT_APPLICABLE)
        except EvaluationError as exc:
            return Result(INDETERMINATE, self.id, reason=str(exc))
        return _with_directives(Result(self.effect, self.id), self, request)


@dataclass
class Policy:
    id: str
    target: Target
    combine: object
    children: list
    obligations: list
    advice: list

    def evaluate(self, request):
        try:
            if not self.target.matches(request):
                return Result(NOT_APPLICABLE)
        except EvaluationError as exc:
            return Result(INDETERMINATE, self.id, reason=str(exc))
        return _with_directives(self.combine(self.children, request), self, request)


def _parse_rule(element):
    effect = _required(element, "Effect")
    if effect not in (PERMIT, DENY):
        raise PolicyError("Rule Effect must be Permit or Deny")
    conditions = _children(element, "Condition")
    if len(conditions) > 1:
        raise PolicyError("A rule has at most one <Condition>")
    condition = None
    if conditions:
        inner = list(conditions[0])
        if len(inner) != 1:
            raise PolicyError("<Condition> needs exactly one expression")
        condition = _parse_expression(inner[0])
    targets = _children(element, "Target")
    return Rule(
        _required(element, "RuleId"),
        effect,
        _parse_target(targets[0] if targets else None),
        condition,
        _obligations(element),
        _advice(element),
    )


ALLOWED_CHILDREN = {
    "PolicySet": {"Description", "Target", "Policy", "PolicySet", "ObligationExpressions", "AdviceExpressions"},
    "Policy": {"Description", "Target", "Rule", "ObligationExpressions", "AdviceExpressions"},
    "Rule": {"Description", "Target", "Condition", "ObligationExpressions", "AdviceExpressions"},
}


def _check_children(element):
    allowed = ALLOWED_CHILDREN[_tag(element)]
    for child in element:
        if _tag(child) not in allowed:
            raise PolicyError(f"Unsupported element <{_tag(child)}> in <{_tag(element)}>")


def _parse_policy(element):
    name = _tag(element)
    _check_children(element)
    targets = _children(element, "Target")
    if name == "Policy":
        rules = []
        for rule in _children(element, "Rule"):
            _check_children(rule)
            rules.append(_parse_rule(rule))
        return Policy(
            _required(element, "PolicyId"),
            _parse_target(targets[0] if targets else None),
            _algorithm(_required(element, "RuleCombiningAlgId")),
            rules,
            _obligations(element),
            _advice(element),
        )
    if name == "PolicySet":
        children = [_parse_policy(c) for c in element if _tag(c) in ("Policy", "PolicySet")]
        return Policy(
            _required(element, "PolicySetId"),
            _parse_target(targets[0] if targets else None),
            _algorithm(_required(element, "PolicyCombiningAlgId")),
            children,
            _obligations(element),
            _advice(element),
        )
    raise PolicyError(f"Expected <Policy> or <PolicySet>, got <{name}>")


def load(text):
    """Parse a policy document. Raises PolicyError if it is not fully supported."""
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise PolicyError("DTDs and entities are not allowed in policies")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise PolicyError(f"Malformed policy XML: {exc}") from None
    if not root.tag.startswith("{" + NS + "}"):
        raise PolicyError(f"Root element must be in the XACML 3.0 namespace {NS}")
    return _parse_policy(root)


def evaluate(policy, request):
    """Evaluate a request; never raises."""
    try:
        return policy.evaluate(request)
    except EvaluationError as exc:  # defensive: evaluation errors are normally caught per rule
        return Result(INDETERMINATE, policy.id, reason=str(exc))

#!/usr/bin/env python3
"""
aggregate.py - merges every scanner's raw report into ONE summary and decides
whether the pipeline passes or fails ("the gate").

Reads : $REPORTS_DIR/*.json + status.txt  (written by scan.sh)
        $SRC_DIR/vulnscan/suppressions.json (accepted risks, optional)
Writes: $REPORTS_DIR/summary.md and summary.json
Exit  : 0 = passed, 1 = gate failed, 2 = configuration error

The gate FAILS when any of these is true:
  * an unsuppressed finding has a severity listed in FAIL_ON
  * a scanner crashed or produced an unreadable report  (fail closed!)
  * STRICT=1 and a scanner was skipped

Only the Python standard library is used, so it runs anywhere.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
from pathlib import Path

# ----------------------------------------------------------------------------
# Configuration (environment variables, defaults set in docker-compose)
# ----------------------------------------------------------------------------
SRC = os.environ.get("SRC_DIR", "/src").rstrip("/")
REPORTS = Path(os.environ.get("REPORTS_DIR", "/reports"))
SUPPRESSIONS_FILE = Path(os.environ.get("SUPPRESSIONS_FILE", f"{SRC}/scripts/vulnscan/suppressions.json"))
STRICT = os.environ.get("STRICT", "0") == "1"

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]  # most -> least serious
# Other tools' wording -> our scale (Semgrep: ERROR/WARNING/INFO, npm: moderate/info).
SEV_ALIASES = {"MODERATE": "MEDIUM", "INFO": "LOW", "INFORMATIONAL": "LOW",
               "ERROR": "HIGH", "WARNING": "MEDIUM"}

FAIL_ON = {s.strip().upper() for s in os.environ.get("FAIL_ON", "CRITICAL,HIGH").split(",") if s.strip()}
TREAT_UNKNOWN_AS = os.environ.get("TREAT_UNKNOWN_AS", "HIGH").strip().upper()

# Django `check --deploy` warnings that are serious for a banking app.
# Everything else that is a warning (W) is MEDIUM; errors (E/C) are HIGH.
DJANGO_HIGH = {"security.W009",  # weak/insecure SECRET_KEY
               "security.W018",  # DEBUG = True
               "security.W012",  # SESSION_COOKIE_SECURE is off
               "security.W016",  # CSRF_COOKIE_SECURE is off
               "security.W020"}  # ALLOWED_HOSTS is empty


class ToolError(Exception):
    """A scanner did not run properly. Treated as a failure, never as 'clean'."""


def config_error(message: str) -> None:
    print(f"CONFIG ERROR: {message}", file=sys.stderr)
    sys.exit(2)


for _s in FAIL_ON | {TREAT_UNKNOWN_AS}:
    if _s not in SEVERITIES:
        config_error(f"unknown severity '{_s}' (valid: {', '.join(SEVERITIES)})")


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def norm_sev(value) -> str:
    v = str(value or "").strip().upper()
    v = SEV_ALIASES.get(v, v)
    return v if v in SEVERITIES else "UNKNOWN"


def effective_sev(finding: dict) -> str:
    """Severity used by the gate (UNKNOWN is mapped to TREAT_UNKNOWN_AS)."""
    return TREAT_UNKNOWN_AS if finding["severity"] == "UNKNOWN" else finding["severity"]


def rel(path) -> str:
    """/src/backend/app.py:12 -> backend/app.py:12 (shorter, host independent)."""
    return str(path or "").replace(SRC + "/", "", 1)


def clip(text, n: int = 160) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def make(tool, fid, severity, title, location="", fix="", aliases=()) -> dict:
    """Common finding format shared by every parser."""
    return {
        "tool": tool,
        "id": str(fid),
        "ids": {str(fid), *map(str, aliases)},  # every name a suppression may use
        "severity": norm_sev(severity),
        "title": clip(title),
        "location": rel(location),
        "fix": fix,
    }


def load_json(path: Path, default=None):
    """Read a JSON report. Missing/corrupt -> ToolError (unless a default is allowed)."""
    if not path.exists():
        if default is not None:
            return default
        raise ToolError(f"report {path.name} was not produced")
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        if default is not None:
            return default
        raise ToolError(f"report {path.name} is empty")
    try:
        return json.loads(text)
    except ValueError as exc:
        raise ToolError(f"report {path.name} is not valid JSON ({exc})")


# ----------------------------------------------------------------------------
# Parsers: one per tool. Each returns (findings, notes).
# ----------------------------------------------------------------------------
def parse_pip_audit(path: Path):
    data = load_json(path)
    if not isinstance(data, dict) or "dependencies" not in data:
        raise ToolError("unexpected pip-audit JSON structure")
    out = []
    for dep in data["dependencies"]:
        name, version = dep.get("name", "?"), dep.get("version", "?")
        for vuln in dep.get("vulns", []):
            fixes = ", ".join(vuln.get("fix_versions") or [])
            out.append(make(
                "pip-audit", vuln.get("id", "?"),
                "UNKNOWN",  # pip-audit gives no severity -> policy decides (TREAT_UNKNOWN_AS)
                f"{name} {version}: {vuln.get('description') or 'known vulnerability'}",
                f"{name}=={version}",
                f"upgrade to {fixes}" if fixes else "no fixed version published yet",
                vuln.get("aliases") or []))
    return out, []


def parse_npm_audit(path: Path):
    data = load_json(path)
    if not isinstance(data, dict):
        raise ToolError("unexpected npm audit JSON structure")
    if "error" in data:  # e.g. registry unreachable
        err = data["error"]
        raise ToolError(clip(err.get("summary") if isinstance(err, dict) else err))
    out = []
    for name, vuln in (data.get("vulnerabilities") or {}).items():
        ghsas, title = [], ""
        for via in vuln.get("via", []):  # `via` mixes advisories (dict) and package names (str)
            if isinstance(via, dict):
                if via.get("url"):
                    ghsas.append(via["url"].rstrip("/").rsplit("/", 1)[-1])
                title = title or via.get("title", "")
        fix_info = vuln.get("fixAvailable")
        if isinstance(fix_info, dict):
            fix = f"upgrade {fix_info.get('name')} to {fix_info.get('version')}"
            if fix_info.get("isSemVerMajor"):
                fix += " (major/breaking)"
        elif fix_info is True:
            fix = "npm audit fix"
        else:
            fix = "no fix available yet"
        out.append(make("npm-audit", ghsas[0] if ghsas else name, vuln.get("severity"),
                        f"{name}: {title or 'vulnerable through a dependency'}",
                        name, fix, [name, *ghsas]))
    return out, []


def parse_bandit(path: Path):
    data = load_json(path)
    if not isinstance(data, dict) or "results" not in data:
        raise ToolError("unexpected Bandit JSON structure")
    out = [make("bandit", r.get("test_id", "?"), r.get("issue_severity"),
                r.get("issue_text", ""), f"{r.get('filename')}:{r.get('line_number')}",
                "", [r.get("test_name", "")])
           for r in data["results"]]
    notes = [f"{len(data['errors'])} file(s) could not be analysed"] if data.get("errors") else []
    return out, notes


def parse_semgrep(path: Path):
    data = load_json(path)
    if not isinstance(data, dict) or "results" not in data:
        raise ToolError("unexpected Semgrep JSON structure")
    out = []
    for r in data["results"]:
        extra = r.get("extra", {})
        rule = r.get("check_id", "?")
        out.append(make("semgrep", rule, extra.get("severity"), extra.get("message", ""),
                        f"{r.get('path')}:{(r.get('start') or {}).get('line', '?')}",
                        "", [rule.rsplit(".", 1)[-1]]))  # suppress by full or short rule name
    errors = [e for e in data.get("errors", []) if str(e.get("level", "")).lower() == "error"]
    notes = [f"{len(errors)} Semgrep error(s) (some files may not be scanned)"] if errors else []
    return out, notes


def parse_gitleaks(path: Path):
    data = load_json(path, default=[])  # gitleaks may write nothing when it finds nothing
    if not isinstance(data, list):
        raise ToolError("unexpected gitleaks JSON structure")
    out = [make("gitleaks", f.get("RuleID", "?"), "CRITICAL",  # a leaked secret is always critical
                f"{f.get('Description', 'secret detected')} (commit {str(f.get('Commit', ''))[:8] or 'working tree'})",
                f"{f.get('File')}:{f.get('StartLine')}",
                "rotate the secret FIRST (it is in git history), then remove it",
                [f.get("Fingerprint", "")])
           for f in data]
    return out, []


def parse_trivy(path: Path):
    data = load_json(path)
    if not isinstance(data, dict):
        raise ToolError("unexpected Trivy JSON structure")
    out = []
    for res in data.get("Results") or []:
        target = res.get("Target", "")
        for v in res.get("Vulnerabilities") or []:
            fixed = v.get("FixedVersion")
            out.append(make("trivy", v.get("VulnerabilityID", "?"), v.get("Severity"),
                            f"{v.get('PkgName')} {v.get('InstalledVersion')}: {v.get('Title') or ''}",
                            target, f"upgrade to {fixed}" if fixed else "no fixed version yet"))
        for s in res.get("Secrets") or []:
            out.append(make("trivy", s.get("RuleID", "?"), s.get("Severity"),
                            s.get("Title", "secret"), f"{target}:{s.get('StartLine', '?')}",
                            "rotate the secret and remove it"))
        for m in res.get("Misconfigurations") or []:
            if str(m.get("Status", "FAIL")).upper() == "PASS":
                continue
            line = (m.get("CauseMetadata") or {}).get("StartLine")
            out.append(make("trivy", m.get("ID", "?"), m.get("Severity"),
                            f"{m.get('Title', '')}: {m.get('Message', '')}",
                            f"{target}:{line}" if line else target,
                            m.get("Resolution", ""), [m.get("AVDID", "")]))
    return out, []


def parse_django_check(path: Path):
    """`python manage.py check --deploy` output (text). Optional, see README."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if "System check" not in text:  # Django prints this line whenever the check really ran
        raise ToolError("django-check.txt does not look like `manage.py check` output")
    out = []
    for m in re.finditer(r"\((?P<id>[a-z_]+\.(?P<kind>[WECI])\d+)\)\s*(?P<msg>.*)", text):
        cid, kind = m["id"], m["kind"]
        sev = "HIGH" if (kind in "EC" or cid in DJANGO_HIGH) else ("MEDIUM" if kind == "W" else "LOW")
        out.append(make("django-check", cid, sev, m["msg"], "Django settings",
                        "see https://docs.djangoproject.com/en/stable/ref/checks/"))
    return out, []


# name -> (report file, exit codes that mean "ran fine", parser)
# Exit 1 is normal for tools that use it to signal "findings exist".
TOOLS = {
    "pip-audit": ("pip-audit.json", {0, 1}, parse_pip_audit),
    "npm-audit": ("npm-audit.json", {0, 1}, parse_npm_audit),
    "bandit":    ("bandit.json",    {0, 1}, parse_bandit),
    "semgrep":   ("semgrep.json",   {0},    parse_semgrep),
    "gitleaks":  ("gitleaks.json",  {0, 1}, parse_gitleaks),
    "trivy":     ("trivy.json",     {0},    parse_trivy),
}


# ----------------------------------------------------------------------------
# Suppressions (accepted risks / false positives)
# ----------------------------------------------------------------------------
def load_suppressions():
    """Each entry needs id + reason + expires (YYYY-MM-DD); tool/path are optional.
    Expired entries stop working, so nothing stays silenced forever."""
    if not SUPPRESSIONS_FILE.exists():
        return [], []
    try:
        raw = json.loads(SUPPRESSIONS_FILE.read_text(encoding="utf-8"))
    except ValueError as exc:
        config_error(f"{SUPPRESSIONS_FILE} is not valid JSON: {exc}")
    if not isinstance(raw, list):
        config_error(f"{SUPPRESSIONS_FILE} must contain a JSON list")
    today = datetime.date.today()
    active, expired = [], []
    for i, entry in enumerate(raw, 1):
        for key in ("id", "reason", "expires"):
            if not isinstance(entry, dict) or not entry.get(key):
                config_error(f"suppression #{i} is missing '{key}' (id, reason and expires are required)")
        try:
            expires = datetime.date.fromisoformat(entry["expires"])
        except ValueError:
            config_error(f"suppression #{i}: 'expires' must look like 2026-12-31")
        (active if expires >= today else expired).append(entry)
    return active, expired


def is_suppressed(finding: dict, suppressions: list):
    for s in suppressions:
        if s["id"] not in finding["ids"]:
            continue
        if s.get("tool") and s["tool"] != finding["tool"]:
            continue
        if s.get("path") and s["path"] not in finding["location"]:
            continue
        return s
    return None


# ----------------------------------------------------------------------------
# Report writers
# ----------------------------------------------------------------------------
def md(text) -> str:
    """Make text safe inside a Markdown table cell."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def build_markdown(passed, reasons, tool_results, counts, blocking, others, suppressed, expired):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Security scan summary", "",
        f"**Result: {'PASSED' if passed else 'FAILED'}**  ",
        f"Gate: fail on {', '.join(s for s in SEVERITIES if s in FAIL_ON)} "
        f"(findings without severity are treated as {TREAT_UNKNOWN_AS}) · {now}", "",
    ]
    if reasons:
        lines += ["## Why it failed", *[f"- {r}" for r in reasons], ""]

    lines += ["## Tools", "", "| Tool | Status | Findings | Notes |", "|---|---|---|---|"]
    for r in tool_results:
        lines.append(f"| {r['name']} | {r['state']} | {r['count']} | {md(r['detail'])} |")

    lines += ["", "## Findings by severity (after suppressions)", "",
              "| " + " | ".join(SEVERITIES) + " |", "|" + "---|" * len(SEVERITIES),
              "| " + " | ".join(str(counts[s]) for s in SEVERITIES) + " |", ""]

    if blocking:
        lines += ["## Findings that fail the gate", "",
                  "| Severity | Tool | ID | Location | Fix | Description |", "|---|---|---|---|---|---|"]
        for f in blocking[:100]:
            lines.append(f"| {f['severity']} | {f['tool']} | {md(f['id'])} | {md(f['location'])} | "
                         f"{md(f['fix'])} | {md(f['title'])} |")
        if len(blocking) > 100:
            lines.append(f"\n…and {len(blocking) - 100} more (see summary.json)")
        lines.append("")

    if others:
        lines += ["<details><summary>Other findings (do not fail the gate)</summary>", "",
                  "| Severity | Tool | ID | Location | Description |", "|---|---|---|---|---|"]
        for f in others[:100]:
            lines.append(f"| {f['severity']} | {f['tool']} | {md(f['id'])} | {md(f['location'])} | {md(f['title'])} |")
        lines += ["", "</details>", ""]

    if suppressed:
        lines += ["## Suppressed findings (accepted risks)", "",
                  "| Tool | ID | Location | Reason | Expires |", "|---|---|---|---|---|"]
        for f, s in suppressed:
            lines.append(f"| {f['tool']} | {md(f['id'])} | {md(f['location'])} | {md(s['reason'])} | {s['expires']} |")
        lines.append("")

    if expired:
        lines += ["## Expired suppressions (no longer applied - review them)", ""]
        lines += [f"- `{s['id']}` expired {s['expires']}: {s['reason']}" for s in expired]
        lines.append("")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def read_status() -> dict:
    """status.txt lines: '<tool> <exit code>'  or  '<tool> SKIPPED <reason>'."""
    status = {}
    path = REPORTS / "status.txt"
    if path.exists():
        for line in path.read_text().splitlines():
            parts = line.split(None, 2)
            if len(parts) >= 2:
                status[parts[0]] = parts[1:]
    return status


def main() -> int:
    suppressions, expired = load_suppressions()
    status = read_status()

    findings, tool_results, reasons = [], [], []

    for name, (report, ok_codes, parser) in TOOLS.items():
        result = {"name": name, "state": "OK", "count": 0, "detail": ""}
        entry = status.get(name)
        try:
            if entry is None:
                raise ToolError("scan.sh recorded no status for this tool")
            if entry[0] == "SKIPPED":
                result["state"] = "SKIPPED"
                result["detail"] = entry[1] if len(entry) > 1 else ""
                if STRICT:
                    reasons.append(f"{name} was skipped and STRICT=1 ({result['detail']})")
            else:
                if not entry[0].isdigit() or int(entry[0]) not in ok_codes:
                    log = REPORTS / f"{name}.log"
                    tail = log.read_text(errors="replace").strip().splitlines()[-3:] if log.exists() else []
                    raise ToolError(f"exit code {entry[0]}" + (f": {clip(' / '.join(tail), 200)}" if tail else ""))
                found, notes = parser(REPORTS / report)
                findings += found
                result["count"] = len(found)
                result["detail"] = "; ".join(notes)
        except ToolError as exc:
            result["state"], result["detail"] = "ERROR", str(exc)
            reasons.append(f"{name} failed to run properly: {exc}")
        tool_results.append(result)

    # Optional: Django deploy check, produced outside this container.
    django_file = REPORTS / "django-check.txt"
    if django_file.exists():
        result = {"name": "django-check", "state": "OK", "count": 0, "detail": ""}
        try:
            found, _ = parse_django_check(django_file)
            findings += found
            result["count"] = len(found)
        except ToolError as exc:
            result["state"], result["detail"] = "ERROR", str(exc)
            reasons.append(f"django-check failed to run properly: {exc}")
        tool_results.append(result)
    else:
        tool_results.append({"name": "django-check", "state": "SKIPPED", "count": 0,
                             "detail": "optional - no django-check.txt (see README)"})

    # Apply suppressions.
    active, suppressed = [], []
    for f in findings:
        s = is_suppressed(f, suppressions)
        (suppressed.append((f, s)) if s else active.append(f))

    order = {s: i for i, s in enumerate(SEVERITIES)}
    active.sort(key=lambda f: (order[f["severity"]], f["tool"], f["location"]))

    blocking = [f for f in active if effective_sev(f) in FAIL_ON]
    others = [f for f in active if effective_sev(f) not in FAIL_ON]
    counts = {s: sum(1 for f in active if f["severity"] == s) for s in SEVERITIES}

    if blocking:
        reasons.insert(0, f"{len(blocking)} unsuppressed finding(s) at or above the gate severity")
    passed = not reasons

    # Write reports.
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "summary.md").write_text(
        build_markdown(passed, reasons, tool_results, counts, blocking, others, suppressed, expired), encoding="utf-8")
    to_json = lambda f: {**f, "ids": sorted(f["ids"])}  # sets are not JSON serialisable
    (REPORTS / "summary.json").write_text(json.dumps({
        "passed": passed, "reasons": reasons, "fail_on": sorted(FAIL_ON), "strict": STRICT,
        "tools": tool_results, "counts": counts,
        "findings": [to_json(f) for f in active],
        "suppressed": [{**to_json(f), "suppression": s} for f, s in suppressed],
        "expired_suppressions": expired,
    }, indent=2), encoding="utf-8")

    # Console summary (what a developer sees in the terminal / CI log).
    print(f"\n=== Security scan: {'PASSED' if passed else 'FAILED'} ===")
    for r in tool_results:
        extra = f"  ({r['detail']})" if r["detail"] else ""
        print(f"  {r['name']:<13}{r['state']:<9}{r['count']:>4} finding(s){extra}")
    print("  by severity: " + ", ".join(f"{s}={counts[s]}" for s in SEVERITIES)
          + f"   | suppressed: {len(suppressed)}")
    for reason in reasons:
        print(f"  ! {reason}")
    for f in blocking[:30]:
        print(f"  - [{f['severity']}] {f['tool']}: {f['id']} @ {f['location']}  {f['fix']}")
    if len(blocking) > 30:
        print(f"  ...and {len(blocking) - 30} more")
    if expired:
        print(f"  note: {len(expired)} suppression(s) expired and are no longer applied")
    print(f"  full report: {REPORTS}/summary.md\n")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
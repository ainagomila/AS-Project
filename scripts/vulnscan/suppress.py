#!/usr/bin/env python3
"""
suppress.py - adds an accepted-risk entry to suppressions.json.

You still make the decision (a reason is mandatory); this only removes the
typing and enforces the rules: reason >= 15 chars, expiry <= 90 days,
no duplicates.

Example:
  python3 scripts/vulnscan/suppress.py DS-0002 --tool trivy \
      --path backend/Dockerfile --reason "Fix planned in PR #12" --days 14
Find the IDs in security-reports/summary.md (column "ID").
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

FILE = Path(__file__).with_name("suppressions.json")
MAX_DAYS = 90

ap = argparse.ArgumentParser(description=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("id", help="finding ID, e.g. CVE-2026-1234, B105, DS-0002")
ap.add_argument("--reason", required=True, help="why this risk is acceptable")
ap.add_argument("--tool", help="limit to one tool (bandit, trivy, ...)")
ap.add_argument("--path", help="limit to files whose path contains this text")
ap.add_argument("--days", type=int, default=14, help=f"validity, max {MAX_DAYS}")
a = ap.parse_args()

if len(a.reason.strip()) < 15:
    sys.exit("Reason too short: explain WHY the risk is acceptable (15+ characters).")
if not 1 <= a.days <= MAX_DAYS:
    sys.exit(f"--days must be between 1 and {MAX_DAYS}.")

entries = json.loads(FILE.read_text()) if FILE.exists() else []
key = (a.id, a.tool, a.path)
if any((e["id"], e.get("tool"), e.get("path")) == key for e in entries):
    sys.exit("That suppression already exists.")

entry = {"id": a.id}
if a.tool:
    entry["tool"] = a.tool
if a.path:
    entry["path"] = a.path
entry["reason"] = a.reason.strip()
entry["expires"] = (datetime.date.today() + datetime.timedelta(days=a.days)).isoformat()
entries.append(entry)

FILE.write_text(json.dumps(entries, indent=2) + "\n")
print(f"Added: {entry['id']} (expires {entry['expires']}) -> {FILE}")
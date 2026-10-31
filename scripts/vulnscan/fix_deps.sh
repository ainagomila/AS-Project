#!/usr/bin/env bash
# fix_deps.sh - upgrades vulnerable dependencies found by the LAST scan.
# Run on your machine from the repo root (needs git, uv, npm):
#   git switch main && git pull
#   docker compose -f docker-compose.security.yml run --rm security-scanner
#   bash scripts/vulnscan/fix_deps.sh
set -euo pipefail

BACKEND="${BACKEND_DIR:-backend}"
FRONTEND="${FRONTEND_DIR:-frontend}"
SUMMARY="security-reports/summary.json"
BACKEND_TEST="${BACKEND_TEST_CMD:-uv run pytest -q}"   # adjust to your test command
FRONTEND_TEST="${FRONTEND_TEST_CMD:-npm run build}"    # adjust (e.g. npm test)

[ -f "$SUMMARY" ] || { echo "Run the scanner first ($SUMMARY is missing)"; exit 1; }
# Refuse to start on a dirty tree so we never mix our changes with yours.
git diff --quiet && git diff --cached --quiet || { echo "Commit or stash your changes first"; exit 1; }

# Names of Python packages and number of npm findings, taken from the scan.
pkgs=$(python3 - "$SUMMARY" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
print(" ".join(sorted({f["location"].split("==")[0]
                       for f in d["findings"] if f["tool"] == "pip-audit"})))
EOF
)
npm_n=$(python3 - "$SUMMARY" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
print(sum(1 for f in d["findings"] if f["tool"] == "npm-audit"))
EOF
)

if [ -z "$pkgs" ] && [ "$npm_n" = "0" ]; then
  echo "No dependency findings to fix."; exit 0
fi

BRANCH="fix/vuln-deps-$(date +%Y%m%d)"
git switch -c "$BRANCH"

# Undo everything and go back to the original branch.
abort() {
  git checkout -- . && git switch - >/dev/null && git branch -D "$BRANCH" >/dev/null
  echo "$1"; exit 1
}

if [ -n "$pkgs" ]; then
  args=(); for p in $pkgs; do args+=(--upgrade-package "$p"); done
  # Upgrades only within the limits set in pyproject.toml.
  ( cd "$BACKEND" && uv lock "${args[@]}" && uv sync && eval "$BACKEND_TEST" ) \
    || abort "Backend upgrade or tests failed - reverted. Upgrade manually."
fi

if [ "$npm_n" != "0" ]; then
  # No --force: breaking major upgrades must be done by hand.
  ( cd "$FRONTEND" && (npm audit fix || true) && eval "$FRONTEND_TEST" ) \
    || abort "Frontend upgrade or build failed - reverted. Upgrade manually."
fi

git add -u -- "$BACKEND" "$FRONTEND"
git diff --cached --quiet && abort "Nothing changed: no compatible fix exists. Upgrade manually or suppress."
git commit -q -m "fix(deps): upgrade vulnerable dependencies (found by vulnscan)"

echo "Done on branch $BRANCH."
echo "1) Re-run the scanner to confirm the findings are gone"
echo "2) git push -u origin $BRANCH  and open a PR"
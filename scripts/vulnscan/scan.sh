#!/usr/bin/env bash
# scan.sh - runs every scanner, saves raw reports in $REPORTS_DIR, then calls
# aggregate.py, whose exit code decides pass/fail for the whole pipeline.
#
# Design rule: this script never decides whether findings are "bad".
# It only records (a) each tool's raw output and (b) its exit code in
# status.txt. aggregate.py applies the policy. That way a crashed scanner
# can never be mistaken for a clean scan.
#
# No "set -e": a scanner exiting non-zero usually just means "I found something".
set -uo pipefail

SRC="${SRC_DIR:-/src}"             # the repository (mounted read-only)
REPORTS="${REPORTS_DIR:-/reports}" # where reports are written
export SRC_DIR="$SRC" REPORTS_DIR="$REPORTS"

mkdir -p "$REPORTS"
# Delete only the files this script owns. (django-check.txt is produced
# outside this container, so it is deliberately kept.)
rm -f "$REPORTS"/{pip-audit,npm-audit,bandit,semgrep,gitleaks,trivy}.{json,log,stdout} \
      "$REPORTS"/status.txt "$REPORTS"/summary.{md,json}
: > "$REPORTS/status.txt"

# ---------- helpers ----------------------------------------------------------

# Append "<tool> <exit code or SKIPPED reason>" to status.txt.
record() { echo "$1 $2" >> "$REPORTS/status.txt"; }

# A tool that cannot run (e.g. no lockfile yet) is recorded as SKIPPED, not OK.
skip() { echo "==> $1: SKIPPED ($2)"; record "$1" "SKIPPED $2"; }

# Run a tool, keep stdout/stderr in files, remember its exit code.
run_tool() {
  local name="$1"; shift
  echo "==> $name"
  "$@" > "$REPORTS/$name.stdout" 2> "$REPORTS/$name.log"
  local rc=$?
  echo "    exit code: $rc"
  record "$name" "$rc"
}

# Find the first file with a given name, ignoring dependency/build folders.
find_first() {
  find "$SRC" -maxdepth 4 -name "$1" \
    -not -path '*/node_modules/*' -not -path '*/.venv/*' \
    -not -path '*/venv/*' -not -path '*/.git/*' | sort | head -n1
}

# ---------- 1. Python dependencies: pip-audit --------------------------------
# The backend uses uv (no requirements.txt). Export the exact versions pinned
# in uv.lock (production deps only) and audit that list.
BACKEND_REL="${BACKEND_DIR:-backend}"
LOCKFILE="$SRC/$BACKEND_REL/uv.lock"
if [ -f "$LOCKFILE" ]; then
  EXPORT="$REPORTS/requirements.export.txt"
  if uv export --project "$SRC/$BACKEND_REL" --frozen --no-dev --no-emit-project \
        --no-hashes -o "$EXPORT" 2> "$REPORTS/pip-audit.log"; then
    run_tool pip-audit pip-audit -r "$EXPORT" --no-deps --disable-pip \
        -f json -o "$REPORTS/pip-audit.json" --progress-spinner off
  else
    echo "==> pip-audit: uv export failed (see pip-audit.log)"
    record pip-audit 99     # 99 = our own "could not run" code -> gate fails closed
  fi
else
  skip pip-audit "no uv.lock in $BACKEND_REL"
fi

# ---------- 2. JavaScript dependencies: npm audit ----------------------------
# Needs package-lock.json so that results are reproducible.
if [ -n "${FRONTEND_DIR:-}" ]; then LOCK="$SRC/$FRONTEND_DIR/package-lock.json"; else LOCK="$(find_first package-lock.json)"; fi
NPM_FLAGS=""
# By default only production dependencies gate the build (dev tools such as
# bundlers never reach users). Set NPM_OMIT_DEV=0 to audit everything.
[ "${NPM_OMIT_DEV:-1}" = "1" ] && NPM_FLAGS="--omit=dev"
if [ -n "$LOCK" ] && [ -f "$LOCK" ]; then
  run_tool npm-audit bash -c 'cd "$1" && shift && exec npm audit --json "$@"' _ "$(dirname "$LOCK")" $NPM_FLAGS
  # npm prints its JSON to stdout, so that file is the report.
  mv -f "$REPORTS/npm-audit.stdout" "$REPORTS/npm-audit.json"
elif [ -n "$(find_first package.json)" ]; then
  skip npm-audit "package.json found but no package-lock.json (commit the lockfile)"
else
  skip npm-audit "no frontend found"
fi

# ---------- 3a. Python source code: Bandit -----------------------------------
# Static analysis for Python-specific problems (hardcoded secrets, weak crypto,
# eval/exec, unsafe subprocess/SQL...). Tests and migrations are excluded.
if [ -n "${BACKEND_DIR:-}" ]; then
  PYDIR="$SRC/$BACKEND_DIR"
else
  MANAGE="$(find_first manage.py)"
  PYDIR=""; [ -n "$MANAGE" ] && PYDIR="$(dirname "$MANAGE")"
fi
if [ -n "$PYDIR" ] && [ -d "$PYDIR" ]; then
  run_tool bandit bandit -r "$PYDIR" -f json -o "$REPORTS/bandit.json" -q \
    -x '*/tests/*,*/test_*.py,*/migrations/*,*/node_modules/*,*/.venv/*,*/venv/*'
else
  skip bandit "no Django backend found (set BACKEND_DIR)"
fi

# ---------- 3b. Whole repo: Semgrep ------------------------------------------
# Pattern-based rules for Django, Python, JavaScript and the OWASP Top 10.
# Rules are downloaded from the Semgrep registry, so this step needs internet.
# If it cannot download them it fails loudly (never "silently clean").
SEMGREP_ARGS=()
for cfg in ${SEMGREP_RULES:-p/django p/python p/javascript p/owasp-top-ten}; do
  SEMGREP_ARGS+=(--config "$cfg")
done
run_tool semgrep semgrep scan "${SEMGREP_ARGS[@]}" --json -o "$REPORTS/semgrep.json" \
  --metrics=off --quiet \
  --exclude node_modules --exclude .venv --exclude venv \
  --exclude vulnscan --exclude security-reports "$SRC"

# ---------- 4. Secrets in code AND git history: gitleaks ---------------------
# git refuses to read a repo owned by another user; inside the container that
# is always the case, so mark it as safe.
git config --global --add safe.directory '*' 2>/dev/null
GITLEAKS_ARGS=(--source "$SRC" --redact --no-banner --report-format json --report-path "$REPORTS/gitleaks.json" --exit-code 0)
[ -f "$SRC/.gitleaks.toml" ] && GITLEAKS_ARGS+=(--config "$SRC/.gitleaks.toml")
[ -e "$SRC/.git" ] || GITLEAKS_ARGS+=(--no-git)   # not a git checkout: scan files only
# --redact: the report never contains the secret itself.
run_tool gitleaks gitleaks detect "${GITLEAKS_ARGS[@]}"

# ---------- 5. Filesystem / Dockerfile / config: Trivy -----------------------
# Second opinion on dependencies (it also reads requirements/lockfiles), plus
# hardcoded secrets and misconfigurations in Dockerfiles and compose files.
run_tool trivy bash -c 'cd "$1" && exec trivy fs \
    --scanners vuln,secret,misconfig --severity HIGH,CRITICAL \
    --skip-dirs "**/.venv" --skip-dirs "**/node_modules" --skip-dirs .git \
    --skip-dirs backend/.certs --skip-dirs backend/.env.d \
    --skip-dirs scripts/vulnscan --skip-dirs security-reports \
    --format json --output "$2" --exit-code 0 --quiet .' _ "$SRC" "$REPORTS/trivy.json"

# ---------- 6. Aggregate + gate ----------------------------------------------
echo "==> aggregating"
python3 "$SRC/scripts/vulnscan/aggregate.py"
RC=$?

# Make reports deletable by the host user (the container runs as root).
chmod -R a+rwX "$REPORTS" 2>/dev/null
exit $RC
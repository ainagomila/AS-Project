# Authenticated OWASP ZAP scan

Seeds the API through ZAP (customer, auditor, operations, admin and a disposable
user), runs one active scan per route and role, and writes
`security-reports/zap-report.html`. **Local test environments only.**

## Requirements

- Docker (the stack is started by `scripts/start-docker.*`)
- [OWASP ZAP](https://www.zaproxy.org/download/) and Java (bundled with the ZAP installers)
- Python 3 with `requests`: `pip install requests`

## One command

Starts the stack in the background, starts the ZAP daemon, waits for both, scans,
and stops the daemon. The stack stays up afterwards.

| System | Command |
| --- | --- |
| Windows (PowerShell) | `.\scripts\start-docker.ps1 -Zap` |
| Linux / macOS | `./scripts/start-docker.sh --zap` |

If the stack is already running, launch only the scan (any system):

```sh
python scripts/zap/run_zap.py      # `python3` on Linux / macOS
```

ZAP is looked up in `ZAP_PATH` (the `zap.bat` / `zap.sh` file or its folder), in
`PATH`, and in the default install folders of each system. Set `ZAP_PATH` if yours is elsewhere.

## Running it again

Safe to repeat. Each run resets ZAP's session, removes the test users left by a
previous run, and deletes the data it created at the end (`KEEP_DATA=1` keeps it).
A ZAP daemon left over from a crashed run is reused, not duplicated: its API key
is kept in `security-reports/.zap-api-key`.

## Options (environment variables)

| Variable | Default | Meaning |
| --- | --- | --- |
| `ZAP_PATH` | auto | `zap.bat` / `zap.sh` or its folder |
| `ZAP_PORT` | `8090` | daemon port |
| `ZAP_API_KEY` | random, saved | ZAP API key |
| `SCAN_AS` | `all` | `customer`, `auditor`, `operations`, `admin` or `all` |
| `KOFRE_BASE` | `https://localhost:8080` | backend URL |
| `KEEP_DATA` | unset | `1` keeps the data created by the run |
| `ZAP_REPORT` | `security-reports/zap-report.html` | report path |

Set them before the command: `$env:SCAN_AS="customer"` (PowerShell) or
`SCAN_AS=customer ./scripts/start-docker.sh --zap` (sh).

## Output

- Console: the `SCAN VERDICT` table (coverage per role, blockers, limits, authorization checks).
- `security-reports/zap-report.html`: ZAP alerts. Review it for tokens and card
  numbers before sharing it. `security-reports/` is git-ignored.
- `security-reports/zap-daemon.log`: ZAP's own log.
- Exit code `0` when coverage is sufficient, `2` when there are blockers.

## Known limits

`pin` is excluded from fuzzing (it would lock the users out); routes with only a
path or only `pin` get probes but no injection; `/o/logout` and `/o/revoke_token`
are excluded; the frontend is out of scope; object-level authorization is checked
by direct requests, not by ZAP.

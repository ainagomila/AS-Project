#!/usr/bin/env python3
"""Start the ZAP daemon in the background, wait for it and for the backend, run the authenticated
scan (zap_scan.py) and stop the daemon again. Works on Windows, Linux and macOS.

Usage: python scripts/zap/run_zap.py   (or start-docker.ps1 -Zap / start-docker.sh --zap)
Env:   ZAP_PATH (zap.bat / zap.sh, or its folder), ZAP_PORT (8090), ZAP_API_KEY (else a random key kept in
       security-reports/.zap-api-key, so re-running reuses a leftover daemon),
       KOFRE_BASE (https://localhost:8080). Needs ZAP, Java and `pip install requests`.
Local test environments only. Exit code: that of zap_scan.py (2 = coverage blockers).
"""
import importlib.util
import json
import os
import secrets
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN = Path(__file__).with_name("zap_scan.py")
PORT = os.getenv("ZAP_PORT", "8090")
ZAP_URL = f"http://127.0.0.1:{PORT}"
BASE = os.getenv("KOFRE_BASE", "https://localhost:8080")
LOG = ROOT / "security-reports" / "zap-daemon.log"
KEY_FILE = ROOT / "security-reports" / ".zap-api-key"


def api_key():
    """ZAP_API_KEY, else the key kept from the last run, so a daemon that outlived a crashed run is reused."""
    key = os.getenv("ZAP_API_KEY")
    if not key and KEY_FILE.is_file():
        key = KEY_FILE.read_text().strip()
    if not key:
        key = secrets.token_hex(16)
        KEY_FILE.parent.mkdir(exist_ok=True)
        KEY_FILE.write_text(key)
    return key


KEY = api_key()


def zap_api(path, timeout=5):
    with urllib.request.urlopen(f"{ZAP_URL}/JSON/{path}/?apikey={KEY}", timeout=timeout) as r:
        return json.load(r)


def zap_up():
    try:
        zap_api("core/view/version")
        return True
    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(error.read())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False
        if payload.get("code") in {"bad_key", "missing_apikey"}:
            sys.exit(
                f"ZAP already answers on {ZAP_URL} but not with this API key: "
                "set ZAP_API_KEY or stop it."
            )
        return False
    except (OSError, ValueError):
        return False


def find_zap():
    names = ("zap.bat",) if os.name == "nt" else ("zap.sh", "zaproxy")
    found, given = [], os.getenv("ZAP_PATH")
    if given:
        p = Path(given)
        found += [p] if p.is_file() else [p / n for n in names]
    found += [Path(w) for w in (shutil.which(n) for n in names) if w]
    if os.name == "nt":
        found += [Path(d) / "ZAP" / "Zed Attack Proxy" / "zap.bat"
                  for d in (os.getenv("ProgramFiles"), os.getenv("ProgramFiles(x86)")) if d]
    elif sys.platform == "darwin":
        found.append(Path("/Applications/ZAP.app/Contents/Java/zap.sh"))
    else:
        found += [Path("/usr/share/zaproxy/zap.sh"), Path("/opt/zaproxy/zap.sh")]
    return next((p for p in found if p.is_file()), None)


def start_zap():
    exe = find_zap()
    if exe is None:
        sys.exit("ZAP not found. Install it (https://www.zaproxy.org/download/) or set ZAP_PATH to zap.bat / zap.sh.")
    LOG.parent.mkdir(exist_ok=True)
    kw = {"cwd": exe.parent, "stdin": subprocess.DEVNULL, "stderr": subprocess.STDOUT, "stdout": open(LOG, "wb")}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    proc = subprocess.Popen([str(exe), "-daemon", "-port", PORT, "-config", f"api.key={KEY}"], **kw)
    print(f"[zap] starting {exe} (log: {LOG})", flush=True)
    deadline = time.time() + 180
    while time.time() < deadline:
        if proc.poll() is not None:
            sys.exit(f"ZAP exited with code {proc.returncode}; see {LOG}")
        if zap_up():
            print("[zap] daemon ready", flush=True)
            return proc
        time.sleep(2)
    proc.terminate()
    sys.exit(f"ZAP did not answer on {ZAP_URL} within 180 s; see {LOG}")


def wait_backend():
    ctx = ssl._create_unverified_context()  # mkcert certificate, local only
    deadline = time.time() + 300
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BASE}/o/.well-known/openid-configuration", timeout=5, context=ctx)
            print("[zap] backend ready", flush=True)
            return
        except urllib.error.HTTPError:
            print("[zap] backend ready", flush=True)  # any HTTP answer means it is up
            return
        except OSError:
            time.sleep(3)
    sys.exit(f"The backend did not answer on {BASE} within 300 s (docker compose logs backend).")


def stop_zap(proc):
    try:
        zap_api("core/action/shutdown", timeout=15)
    except (OSError, ValueError):
        pass
    try:
        proc.wait(30)
    except subprocess.TimeoutExpired:
        proc.terminate()


def main():
    if importlib.util.find_spec("requests") is None:
        sys.exit("Missing dependency: pip install requests")
    proc = None if zap_up() else start_zap()  # an already running ZAP is reused and left running
    try:
        wait_backend()
        env = {**os.environ, "ZAP_API_KEY": KEY, "ZAP_URL": ZAP_URL}
        return subprocess.run([sys.executable, str(SCAN)], cwd=ROOT, env=env).returncode
    finally:
        if proc is not None:
            stop_zap(proc)
            print("[zap] daemon stopped", flush=True)


if __name__ == "__main__":
    sys.exit(main())

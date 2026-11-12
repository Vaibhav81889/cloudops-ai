import logging
import sys
import time
import sqlite3
import db
import alerts

import requests

# Logging: writes to both a file and the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("monitor.log"), logging.StreamHandler()],
)

TIMEOUT_SECONDS = 5       # give up after 5s instead of hanging forever
SLOW_THRESHOLD_SECONDS = 2  # warn if a response takes longer than this
FAILURES_BEFORE_ALERT = 2  # consecutive DOWN checks required to open an incident


def check_website(url: str) -> dict:
    """Check one URL and return a result dictionary."""
    result = {"url": url, "status": "DOWN", "status_code": None,
              "response_time": None, "error": None}
    start = time.perf_counter()  # high-precision timer
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        result["response_time"] = round(time.perf_counter() - start, 3)
        result["status_code"] = response.status_code
        if response.status_code < 400:
            result["status"] = "UP"
        else:
            result["error"] = f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        result["error"] = f"Timeout after {TIMEOUT_SECONDS}s"
    except requests.exceptions.SSLError:
        result["error"] = "SSL certificate error"
    except requests.exceptions.ConnectionError:
        result["error"] = "Connection failed (DNS or refused)"
    except requests.exceptions.RequestException as exc:
        result["error"] = f"Request error: {exc}"
    return result

def handle_incident(r: dict) -> None:
    """Open/close incidents based on state changes and alert once per change."""
    open_inc = db.get_open_incident(r["url"])
    if r["status"] == "DOWN":
        failures = db.count_consecutive_failures(r["url"], FAILURES_BEFORE_ALERT)
        if open_inc is None and failures >= FAILURES_BEFORE_ALERT:
            db.open_incident(r["url"], r["error"])
            alerts.send_alert(f"INCIDENT OPENED: {r['url']} is DOWN ({r['error']})")
    elif open_inc is not None:
        db.resolve_incident(open_inc["id"])
        alerts.send_alert(f"RECOVERED: {r['url']} is back UP (incident #{open_inc['id']})")

def main() -> None:
    db.init_db()
    urls = sys.argv[1:] or ["https://example.com"]
    for url in urls:
        r = check_website(url)
        try:
            db.save_check(r)
            handle_incident(r)
        except sqlite3.Error:
            logging.exception("Could not save result or update incidents")
        if r["status"] == "UP":
            level = logging.WARNING if r["response_time"] > SLOW_THRESHOLD_SECONDS else logging.INFO
            logging.log(level, "%s UP code=%s time=%ss", r["url"], r["status_code"], r["response_time"])
        else:
            logging.error("%s DOWN reason=%s", r["url"], r["error"])


if __name__ == "__main__":
    main()

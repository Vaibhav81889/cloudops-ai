import argparse
import logging
import sqlite3
import sys
import time
import tomllib
import system_metrics

import requests

import alerts
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("monitor.log"), logging.StreamHandler()],
)


def load_config(path: str) -> dict:
    """Read and validate the TOML config file."""
    with open(path, "rb") as f:  # tomllib requires binary mode
        cfg = tomllib.load(f)
    urls = cfg.get("urls")
    if not isinstance(urls, list) or not urls:
        raise ValueError("config 'urls' must be a non-empty list")
    cfg.setdefault("interval_seconds", 60)
    cfg.setdefault("timeout_seconds", 5)
    cfg.setdefault("slow_threshold_seconds", 2)
    cfg.setdefault("failures_before_alert", 2)
    if cfg["interval_seconds"] < 10:
        raise ValueError("interval_seconds must be at least 10")
    return cfg


def check_website(url: str, timeout: float) -> dict:
    """Check one URL and return a result dictionary."""
    result = {"url": url, "status": "DOWN", "status_code": None,
              "response_time": None, "error": None}
    start = time.perf_counter()
    try:
        response = requests.get(url, timeout=timeout)
        result["response_time"] = round(time.perf_counter() - start, 3)
        result["status_code"] = response.status_code
        if response.status_code < 200:
            result["status"] = "UP"
        else:
            result["error"] = f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        result["error"] = f"Timeout after {timeout}s"
    except requests.exceptions.SSLError:
        result["error"] = "SSL certificate error"
    except requests.exceptions.ConnectionError:
        result["error"] = "Connection failed (DNS or refused)"
    except requests.exceptions.RequestException as exc:
        result["error"] = f"Request error: {exc}"
    return result


def handle_incident(r: dict, failures_before_alert: int) -> None:
    """Open/close incidents based on state changes and alert once per change."""
    open_inc = db.get_open_incident(r["url"])
    if r["status"] == "DOWN":
        failures = db.count_consecutive_failures(r["url"], failures_before_alert)
        if open_inc is None and failures >= failures_before_alert:
            db.open_incident(r["url"], r["error"])
            alerts.send_alert(f"INCIDENT OPENED: {r['url']} is DOWN ({r['error']})")
    elif open_inc is not None:
        db.resolve_incident(open_inc["id"])
        alerts.send_alert(f"RECOVERED: {r['url']} is back UP (incident #{open_inc['id']})")

def run_system_check(sys_cfg: dict) -> None:
    """Collect machine metrics, store them, and check thresholds."""
    try:
        m = system_metrics.collect_metrics()
        db.save_metrics(m)
        logging.info("SYSTEM cpu=%s%% mem=%s%% disk=%s%%",
                     m["cpu_percent"], m["memory_percent"], m["disk_percent"])
        system_metrics.check_thresholds(sys_cfg, sys_cfg.get("breaches_before_alert", 2))
    except (sqlite3.Error, OSError):
        logging.exception("System metrics check failed")

def run_cycle(cfg: dict) -> None:
    """Check every configured URL once."""
    for url in cfg["urls"]:
        r = check_website(url, cfg["timeout_seconds"])
        try:
            db.save_check(r)
            handle_incident(r, cfg["failures_before_alert"])
        except sqlite3.Error:
            logging.exception("Could not save result or update incidents")
        if r["status"] == "UP":
            slow = r["response_time"] > cfg["slow_threshold_seconds"]
            logging.log(logging.WARNING if slow else logging.INFO,
                        "%s UP code=%s time=%ss", r["url"], r["status_code"], r["response_time"])
        else:
            logging.error("%s DOWN reason=%s", r["url"], r["error"])
    run_system_check(cfg.get("system", {}))


def main() -> None:
    parser = argparse.ArgumentParser(description="CloudOps AI uptime monitor")
    parser.add_argument("--config", default="config.toml", help="path to config file")
    parser.add_argument("--once", action="store_true", help="run one cycle and exit")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        logging.error("Config problem: %s", exc)
        sys.exit(1)

    db.init_db()
    db.init_metrics_table()
    if args.once:
        run_cycle(cfg)
        return

    logging.info("Monitoring %d URLs every %ss. Press Ctrl+C to stop.",
                 len(cfg["urls"]), cfg["interval_seconds"])
    try:
        while True:
            run_cycle(cfg)
            time.sleep(cfg["interval_seconds"])
    except KeyboardInterrupt:
        logging.info("Monitor stopped by user")


if __name__ == "__main__":
    main()

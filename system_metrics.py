import argparse
import json
import alerts
import db
from datetime import datetime, timezone

import psutil

GB = 1024 ** 3


def top_processes(count: int = 5) -> list:
    """Return the processes using the most memory."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent"]):
        info = p.info  # dict of the attributes requested above
        info["memory_percent"] = round(info["memory_percent"] or 0, 2)
        procs.append(info)
    procs.sort(key=lambda x: x["memory_percent"], reverse=True)
    return procs[:count]


def collect_metrics() -> dict:
    """Take one snapshot of system health."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_cores": psutil.cpu_count(logical=True),
        "load_avg_1m": round(psutil.getloadavg()[0], 2),
        "memory_percent": mem.percent,
        "memory_used_gb": round(mem.used / GB, 2),
        "memory_total_gb": round(mem.total / GB, 2),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / GB, 2),
        "top_processes": top_processes(5),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="CloudOps AI system metrics snapshot")
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    args = parser.parse_args()

    m = collect_metrics()
    if args.json:
        print(json.dumps(m, indent=2))
        return

    print(f"Time (UTC): {m['collected_at']}")
    print(f"CPU:    {m['cpu_percent']}% across {m['cpu_cores']} cores | load(1m): {m['load_avg_1m']}")
    print(f"Memory: {m['memory_percent']}% ({m['memory_used_gb']} / {m['memory_total_gb']} GB)")
    print(f"Disk /: {m['disk_percent']}% used, {m['disk_free_gb']} GB free")
    print("Top processes by memory:")
    for p in m["top_processes"]:
        print(f"  pid={p['pid']:<7} {p['memory_percent']:>5}%  {p['name']}")

RESOURCE_CHECKS = {"cpu": "cpu_percent", "memory": "memory_percent", "disk": "disk_percent"}


def check_thresholds(limits: dict, consecutive: int) -> None:
    """Alert when a resource is above its limit for N checks in a row."""
    recent = db.get_recent_metrics(consecutive)
    if len(recent) < consecutive:
        return  # not enough history yet
    for name, column in RESOURCE_CHECKS.items():
        limit = limits.get(column)
        if limit is None:
            continue
        key = f"system:{name}"  # reuses the incidents table, keyed per resource
        latest = recent[0][column]
        breached = all(row[column] is not None and row[column] >= limit for row in recent)
        open_inc = db.get_open_incident(key)
        if breached and open_inc is None:
            db.open_incident(key, f"{name} at {latest}% (limit {limit}%)")
            alerts.send_alert(f"RESOURCE ALERT: {name} at {latest}% (limit {limit}%, {consecutive} checks in a row)")
        elif open_inc is not None and latest < limit:
            db.resolve_incident(open_inc["id"])
            alerts.send_alert(f"RESOURCE RECOVERED: {name} back to {latest}% (limit {limit}%)")


if __name__ == "__main__":
    main()

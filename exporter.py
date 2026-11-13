from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.core import GaugeMetricFamily

import db


class CloudOpsCollector:
    """Builds fresh metrics from the SQLite database on every scrape."""

    def collect(self):
        up = GaugeMetricFamily(
            "cloudops_site_up", "1 if the latest check was UP, 0 if DOWN", labels=["url"])
        rt = GaugeMetricFamily(
            "cloudops_site_response_seconds", "Response time of the latest check", labels=["url"])
        for row in db.get_latest_checks():
            up.add_metric([row["url"]], 1 if row["status"] == "UP" else 0)
            if row["response_time"] is not None:
                rt.add_metric([row["url"]], row["response_time"])
        yield up
        yield rt

        incidents = GaugeMetricFamily("cloudops_open_incidents", "Number of unresolved incidents")
        incidents.add_metric([], len(db.get_incidents(open_only=True, limit=1000)))
        yield incidents

        latest = db.get_recent_metrics(1)
        if latest:
            m = latest[0]
            for name, column in (("cpu", "cpu_percent"), ("memory", "memory_percent"),
                                 ("disk", "disk_percent")):
                g = GaugeMetricFamily(f"cloudops_system_{name}_percent",
                                      f"Latest {name} usage percent")
                g.add_metric([], m[column])
                yield g


def render_metrics() -> bytes:
    registry = CollectorRegistry()
    registry.register(CloudOpsCollector())
    return generate_latest(registry)

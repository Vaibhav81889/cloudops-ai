import argparse

import numpy as np
from sklearn.ensemble import IsolationForest

import anomaly
import db

FEATURES = ["cpu_percent", "memory_percent", "load_avg_1m"]
MIN_ROWS = 100  # fewer readings than this: no verdict


def find_ml_anomalies(rows, contamination=0.02, seed=42):
    """Return the indexes of rows an Isolation Forest finds unusual."""
    if len(rows) < MIN_ROWS:
        return []
    X = np.array([[r[f] for f in FEATURES] for r in rows], dtype=float)
    model = IsolationForest(n_estimators=200, contamination=contamination, random_state=seed)
    labels = model.fit_predict(X)  # -1 = anomaly, 1 = normal
    return [i for i, label in enumerate(labels) if label == -1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Isolation Forest on system metrics")
    parser.add_argument("--limit", type=int, default=2000, help="readings to analyse")
    parser.add_argument("--contamination", type=float, default=0.02,
                        help="share of readings to treat as unusual")
    args = parser.parse_args()

    db.init_db()
    db.init_metrics_table()
    rows = [r for r in reversed(db.get_recent_metrics(args.limit))
            if all(r[f] is not None for f in FEATURES)]
    if len(rows) < MIN_ROWS:
        print(f"Only {len(rows)} system readings, need {MIN_ROWS}. Keep the monitor running.")
        return

    ml = set(find_ml_anomalies(rows, args.contamination))
    stats = {a["index"] for a in anomaly.find_anomalies([r["cpu_percent"] for r in rows])}

    print(f"{len(rows)} system readings analysed")
    print(f"Isolation Forest flagged {len(ml)}; statistics (CPU only) flagged {len(stats)}")
    print(f"Agree: {len(ml & stats)} | only ML: {len(ml - stats)} | only statistics: {len(stats - ml)}")
    print("Readings only the ML model flagged (newest first, up to 10):")
    for i in sorted(ml - stats, reverse=True)[:10]:
        r = rows[i]
        print(f"  {r['collected_at']}  cpu={r['cpu_percent']}%  "
              f"mem={r['memory_percent']}%  load={r['load_avg_1m']}")
    print("Suggested action: compare these times with your Grafana dashboard. "
          "No automatic action was taken.")


if __name__ == "__main__":
    main()

import argparse
import statistics

import db

THRESHOLD = 3.5    # modified z-score above this counts as an anomaly
MIN_HISTORY = 30   # fewer readings than this: no verdict
MAD_FLOOR = 0.005  # seconds; stops tiny jitter looking huge on very steady sites
MIN_RATIO = 1.5    # a slow reading must also be 1.5x the normal value


def find_anomalies(values, threshold=THRESHOLD, min_history=MIN_HISTORY):
    """Return unusually SLOW readings from a list of response times (oldest first)."""
    if len(values) < min_history:
        return []
    median = statistics.median(values)
    mad = statistics.median(abs(v - median) for v in values)
    mad = max(mad, MAD_FLOOR)
    anomalies = []
    for i, v in enumerate(values):
        score = 0.6745 * (v - median) / mad
        if score > threshold and v > median * MIN_RATIO:
            anomalies.append({"index": i, "value": v, "score": round(score, 1)})
    return anomalies


def main() -> None:
    parser = argparse.ArgumentParser(description="Flag unusually slow responses")
    parser.add_argument("--limit", type=int, default=500, help="readings per site to analyse")
    parser.add_argument("--recent", type=int, default=20,
                        help="report anomalies among the newest N readings")
    args = parser.parse_args()

    db.init_db()
    for row in db.get_latest_checks():
        url = row["url"]
        readings = db.get_response_times(url, args.limit)
        values = [r["response_time"] for r in readings]
        if len(values) < MIN_HISTORY:
            print(f"{url}: only {len(values)} readings, need {MIN_HISTORY}. Keep the monitor running.")
            continue
        found = find_anomalies(values)
        recent = [a for a in found if a["index"] >= len(values) - args.recent]
        median_ms = statistics.median(values) * 1000
        print(f"{url}: {len(values)} readings, normal ~{median_ms:.0f} ms, "
              f"{len(found)} slow outliers in total, {len(recent)} among the newest {args.recent}")
        for a in recent:
            when = readings[a["index"]]["checked_at"]
            print(f"  ANOMALY {when}  {a['value'] * 1000:.0f} ms  (score {a['score']})")
        if recent:
            print("  Suggested action: check the site and your network manually. "
                  "No automatic action was taken.")


if __name__ == "__main__":
    main()

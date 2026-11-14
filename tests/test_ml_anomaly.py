import random

import ml_anomaly


def calm_rows(n=200, seed=1):
    """A calm machine: CPU ~10%, memory ~50%, load ~0.5, with natural variation."""
    rng = random.Random(seed)
    return [{"cpu_percent": rng.gauss(10, 2),
             "memory_percent": rng.gauss(50, 0.5),
             "load_avg_1m": rng.gauss(0.5, 0.1)} for _ in range(n)]


def test_too_few_readings_gives_no_verdict():
    assert ml_anomaly.find_ml_anomalies(calm_rows(20)) == []


def test_obvious_outlier_is_flagged():
    rows = calm_rows() + [{"cpu_percent": 99.0, "memory_percent": 95.0, "load_avg_1m": 9.0}]
    flagged = ml_anomaly.find_ml_anomalies(rows, contamination=0.02)
    assert len(rows) - 1 in flagged


def test_flags_about_the_requested_share():
    flagged = ml_anomaly.find_ml_anomalies(calm_rows(200), contamination=0.02)
    assert 3 <= len(flagged) <= 5  # 2% of 200 readings is 4

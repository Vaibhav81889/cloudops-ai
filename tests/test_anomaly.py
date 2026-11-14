import anomaly


def steady(n=40, base=0.2):
    """A steady site with a little natural jitter."""
    return [base + (0.005 if i % 2 else -0.005) for i in range(n)]


def test_too_little_history_gives_no_verdict():
    assert anomaly.find_anomalies([0.2, 5.0, 0.2]) == []


def test_normal_jitter_is_not_flagged():
    assert anomaly.find_anomalies(steady()) == []


def test_spike_is_flagged():
    found = anomaly.find_anomalies(steady() + [1.5])
    assert [a["index"] for a in found] == [40]
    assert found[0]["value"] == 1.5


def test_faster_than_normal_is_not_flagged():
    assert anomaly.find_anomalies(steady() + [0.01]) == []


def test_constant_series_does_not_crash():
    assert anomaly.find_anomalies([0.2] * 40) == []


def test_constant_series_with_spike_is_flagged():
    found = anomaly.find_anomalies([0.2] * 40 + [2.0])
    assert len(found) == 1

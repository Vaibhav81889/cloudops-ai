import pytest
import db
import monitor
from datetime import datetime, timedelta, timezone

URL = "https://x.test"


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    # cloudops.db is a relative path, so a temp working directory = a fresh database
    monkeypatch.chdir(tmp_path)
    db.init_db()


@pytest.fixture
def sent_alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(monitor.alerts, "send_alert", sent.append)  # record, don't really alert
    return sent


def down():
    return {"url": URL, "status": "DOWN", "status_code": None,
            "response_time": None, "error": "Timeout"}


def up():
    return {"url": URL, "status": "UP", "status_code": 200,
            "response_time": 0.1, "error": None}


def record(result, threshold=2, max_gap_seconds=None):
    """Same two steps monitor.run_cycle does for each check."""
    db.save_check(result)
    monitor.handle_incident(result, threshold, max_gap_seconds)


def test_single_failure_does_not_alert(sent_alerts):
    record(down())
    assert sent_alerts == []
    assert db.get_open_incident(URL) is None


def test_two_failures_open_one_incident(sent_alerts):
    record(down())
    record(down())
    record(down())  # still down: must NOT alert again
    assert len(sent_alerts) == 1
    assert "INCIDENT OPENED" in sent_alerts[0]
    assert db.get_open_incident(URL) is not None


def test_recovery_closes_incident(sent_alerts):
    record(down())
    record(down())
    record(up())
    assert len(sent_alerts) == 2
    assert "RECOVERED" in sent_alerts[1]
    assert db.get_open_incident(URL) is None


def test_success_in_between_resets_failure_count(sent_alerts):
    record(down())
    record(up())
    record(down())
    assert sent_alerts == []

def insert_down(minutes_ago):
    when = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")
    conn = db.get_connection()
    try:
        conn.execute(
            "INSERT INTO checks (checked_at, url, status, status_code, response_time, error) "
            "VALUES (?, ?, 'DOWN', NULL, NULL, 'Timeout')",
            (when, URL),
        )
        conn.commit()
    finally:
        conn.close()
    return when


def test_failure_before_a_long_gap_does_not_count(sent_alerts):
    insert_down(minutes_ago=180)
    record(down(), threshold=2, max_gap_seconds=180)
    assert sent_alerts == []
    assert db.get_open_incident(URL) is None


def test_failures_close_together_still_count(sent_alerts):
    insert_down(minutes_ago=1)
    record(down(), threshold=2, max_gap_seconds=180)
    assert len(sent_alerts) == 1


def test_incident_starts_at_the_first_failure(sent_alerts):
    first = insert_down(minutes_ago=2)
    insert_down(minutes_ago=1)
    record(down(), threshold=3, max_gap_seconds=180)
    assert db.get_open_incident(URL)["started_at"] == first


def test_config_rejects_zero_failure_threshold(tmp_path):
    cfg = tmp_path / "c.toml"
    cfg.write_text('urls = ["https://x.test"]\nfailures_before_alert = 0\n')
    with pytest.raises(ValueError):
        monitor.load_config(str(cfg))

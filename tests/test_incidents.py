import pytest

import db
import monitor

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


def record(result, threshold=2):
    """Same two steps monitor.run_cycle does for each check."""
    db.save_check(result)
    monitor.handle_incident(result, threshold)


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

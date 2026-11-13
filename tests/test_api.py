import pytest
from fastapi.testclient import TestClient

import db
from api import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # fresh empty database for every test
    with TestClient(app) as c:   # 'with' runs the startup code that creates the tables
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_checks_returns_stored_rows(client):
    db.save_check({"url": "https://x.test", "status": "UP", "status_code": 200,
                   "response_time": 0.1, "error": None})
    r = client.get("/checks?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["url"] == "https://x.test"


def test_checks_rejects_bad_limit(client):
    assert client.get("/checks?limit=0").status_code == 422


def test_open_incidents_filter(client):
    db.open_incident("https://a.test", "Timeout")
    db.open_incident("https://b.test", "Timeout")
    inc = db.get_open_incident("https://b.test")
    db.resolve_incident(inc["id"])
    r = client.get("/incidents?open_only=true")
    assert [i["url"] for i in r.json()] == ["https://a.test"]


def test_system_latest_404_when_empty(client):
    assert client.get("/system/latest").status_code == 404

def test_prometheus_metrics_down_site(client):
    db.save_check({"url": "https://x.test", "status": "DOWN", "status_code": None,
                   "response_time": None, "error": "Timeout"})
    db.open_incident("https://x.test", "Timeout")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert 'cloudops_site_up{url="https://x.test"} 0.0' in r.text
    assert "cloudops_open_incidents 1.0" in r.text


def test_prometheus_metrics_up_site(client):
    db.save_check({"url": "https://ok.test", "status": "UP", "status_code": 200,
                   "response_time": 0.25, "error": None})
    text = client.get("/metrics").text
    assert 'cloudops_site_up{url="https://ok.test"} 1.0' in text
    assert 'cloudops_site_response_seconds{url="https://ok.test"} 0.25' in text

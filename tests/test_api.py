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

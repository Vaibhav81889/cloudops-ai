import requests

import monitor


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_up_on_200(monkeypatch):
    monkeypatch.setattr(monitor.requests, "get", lambda url, timeout: FakeResponse(200))
    r = monitor.check_website("https://x.test", timeout=5)
    assert r["status"] == "UP"
    assert r["status_code"] == 200
    assert r["error"] is None


def test_down_on_404(monkeypatch):
    monkeypatch.setattr(monitor.requests, "get", lambda url, timeout: FakeResponse(404))
    r = monitor.check_website("https://x.test", timeout=5)
    assert r["status"] == "DOWN"
    assert r["error"] == "HTTP 404"


def test_timeout_is_reported(monkeypatch):
    def boom(url, timeout):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(monitor.requests, "get", boom)
    r = monitor.check_website("https://x.test", timeout=5)
    assert r["status"] == "DOWN"
    assert "Timeout" in r["error"]
    assert r["status_code"] is None


def test_connection_error_is_reported(monkeypatch):
    def boom(url, timeout):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr(monitor.requests, "get", boom)
    r = monitor.check_website("https://x.test", timeout=5)
    assert r["status"] == "DOWN"
    assert "Connection failed" in r["error"]

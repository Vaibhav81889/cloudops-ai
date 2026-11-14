import urllib.error

import pytest

import db
import summary

URL = "https://x.test"


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # fresh database per test
    db.init_db()


def down_check():
    return {"url": URL, "status": "DOWN", "status_code": None,
            "response_time": None, "error": "Timeout after 5s"}


@pytest.mark.parametrize("error, word", [
    ("Timeout after 5s", "latency"),
    ("Connection failed (DNS or refused)", "DNS"),
    ("SSL certificate error", "certificate"),
    ("HTTP 503", "application logs"),
    ("HTTP 404", "URL"),
])
def test_advice_matches_error_type(error, word):
    assert word in summary.advice_for(error)


def test_open_incident_facts(clean_db):
    db.save_check(down_check())
    db.save_check(down_check())
    db.open_incident(URL, "Timeout after 5s")
    facts = summary.build_facts(db.get_incident())
    assert facts["status"] == "open"
    assert facts["down_checks"] == 2


def test_resolved_incident_facts(clean_db):
    db.open_incident(URL, "Timeout after 5s")
    db.resolve_incident(db.get_incident()["id"])
    facts = summary.build_facts(db.get_incident())
    assert facts["status"] == "resolved"
    assert facts["duration_minutes"] >= 0


def test_summary_never_claims_to_act(clean_db):
    db.open_incident(URL, "Timeout after 5s")
    text = summary.render_text(summary.build_facts(db.get_incident()))
    assert "No automatic action was taken." in text


def test_llm_failure_returns_none(monkeypatch):
    def boom(*args, **kwargs):
        raise urllib.error.URLError("model server is down")

    monkeypatch.setattr(summary.urllib.request, "urlopen", boom)
    assert summary.ask_local_llm({"url": URL}, "any-model") is None

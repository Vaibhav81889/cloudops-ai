import argparse
import json
import statistics
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import db

LOOKBACK = timedelta(minutes=10)  # include checks from just before the incident opened
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"  # local model server, localhost only


def advice_for(error) -> str:
    """Rule-based next step for a given error text."""
    e = (error or "").lower()
    if "timeout" in e:
        return "Check network latency and server load; the site may be overloaded or unreachable."
    if "connection failed" in e:
        return "Check DNS and your network first (getent hosts <site>, ping), then whether the server is running."
    if "ssl" in e:
        return "Check whether the site's TLS certificate has expired or is misconfigured."
    if "http 5" in e:
        return "The server answered with an error: check the application logs."
    if "http 4" in e:
        return "The server rejected the request: check the URL, authentication and recent config changes."
    return "Check the error message and any recent changes."


def build_facts(incident) -> dict:
    """Collect the facts about one website incident from the database."""
    start = datetime.fromisoformat(incident["started_at"])
    resolved = incident["resolved_at"]
    end = datetime.fromisoformat(resolved) if resolved else datetime.now(timezone.utc)
    checks = db.get_checks_between(
        incident["url"],
        (start - LOOKBACK).isoformat(timespec="seconds"),
        end.isoformat(timespec="seconds"),
    )
    down = [c for c in checks if c["status"] == "DOWN"]
    healthy_times = [c["response_time"] for c in checks
                     if c["status"] == "UP" and c["response_time"] is not None]
    return {
        "incident_id": incident["id"],
        "url": incident["url"],
        "status": "resolved" if resolved else "open",
        "started_at": incident["started_at"],
        "resolved_at": resolved,
        "duration_minutes": round((end - start).total_seconds() / 60, 1),
        "reason": incident["reason"],
        "down_checks": len(down),
        "total_checks_in_window": len(checks),
        "typical_healthy_response_ms": (
            round(statistics.median(healthy_times) * 1000) if healthy_times else None),
        "advice": advice_for(incident["reason"]),
    }


def render_text(f: dict) -> str:
    lines = [
        f"Incident #{f['incident_id']} on {f['url']} ({f['status']})",
        f"Started:  {f['started_at']}",
        f"Resolved: {f['resolved_at'] or 'not yet'}",
        f"Duration: {f['duration_minutes']} minutes",
        f"Reason:   {f['reason']}",
        f"Failed checks in window: {f['down_checks']} of {f['total_checks_in_window']}",
    ]
    if f["typical_healthy_response_ms"] is not None:
        lines.append(f"Typical healthy response in window: {f['typical_healthy_response_ms']} ms")
    lines.append(f"Suggested next step: {f['advice']}")
    lines.append("No automatic action was taken.")
    return "\n".join(lines)


def ask_local_llm(facts: dict, model: str, timeout: int = 120):
    """OPTIONAL: ask a local LLM to rephrase the facts. Returns None on any failure."""
    prompt = (
        "You are helping an on-call engineer. Summarise this website incident in three short "
        "sentences of plain English. Use only the facts below. Do not invent causes. "
        "Do not suggest commands that change anything.\n\nFACTS (JSON):\n" + json.dumps(facts)
    )
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())["response"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise an incident")
    parser.add_argument("--id", type=int, default=None, help="incident id (default: newest)")
    parser.add_argument("--llm", metavar="MODEL", default=None,
                        help="optional: local Ollama model name to rephrase the summary")
    args = parser.parse_args()

    db.init_db()
    incident = db.get_incident(args.id)
    if incident is None:
        print("No incidents recorded yet.")
        return
    if incident["url"].startswith("system:"):
        print(f"Incident #{incident['id']} is a resource incident ({incident['url']}): "
              f"{incident['reason']}. Check the System Usage panel in Grafana.")
        return

    facts = build_facts(incident)
    print(render_text(facts))
    if args.llm:
        answer = ask_local_llm(facts, args.llm)
        print("\nAI-generated summary (untrusted text, verify before acting):")
        print(answer or "Could not reach a local LLM. The facts above are still valid.")


if __name__ == "__main__":
    main()

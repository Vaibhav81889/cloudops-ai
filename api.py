from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts: make sure the tables exist
    db.init_db()
    db.init_metrics_table()
    yield


app = FastAPI(title="CloudOps AI API", version="0.1.0", lifespan=lifespan)


def rows_to_dicts(rows) -> list:
    return [dict(r) for r in rows]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/checks")
def list_checks(limit: int = Query(10, ge=1, le=200)) -> list:
    return rows_to_dicts(db.get_recent_checks(limit))


@app.get("/incidents")
def list_incidents(open_only: bool = False, limit: int = Query(50, ge=1, le=200)) -> list:
    return rows_to_dicts(db.get_incidents(open_only, limit))


@app.get("/system/latest")
def latest_system() -> dict:
    rows = db.get_recent_metrics(1)
    if not rows:
        raise HTTPException(status_code=404, detail="No system metrics stored yet")
    return dict(rows[0])

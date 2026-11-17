"""SQLite session storage."""
import json
import pathlib
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "sessions.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
               id TEXT PRIMARY KEY,
               created_at TEXT NOT NULL,
               candidate_name TEXT,
               role TEXT NOT NULL,
               profile_json TEXT NOT NULL,
               questions_json TEXT NOT NULL
           )""")
    return conn


def save_session(candidate_name: str, role: str, profile: dict,
                 questions: list) -> str:
    sid = uuid.uuid4().hex[:12]
    profile_public = {k: v for k, v in profile.items() if k != "raw_text"}
    with _conn() as conn:
        conn.execute(
            "INSERT INTO sessions VALUES (?,?,?,?,?,?)",
            (sid, datetime.now(timezone.utc).isoformat(), candidate_name,
             role, json.dumps(profile_public), json.dumps(questions)))
    return sid


def get_session(sid: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, created_at, candidate_name, role, profile_json, "
            "questions_json FROM sessions WHERE id = ?", (sid,)).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "created_at": row[1], "candidate_name": row[2],
        "role": row[3], "profile": json.loads(row[4]),
        "questions": json.loads(row[5]),
    }


def list_sessions(limit: int = 20) -> list:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, created_at, candidate_name, role FROM sessions "
            "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r[0], "created_at": r[1], "candidate_name": r[2],
             "role": r[3]} for r in rows]

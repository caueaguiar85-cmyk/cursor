"""
Stoken Advisory — Database-backed Data Store
Persiste entrevistas, resultados de análise e insights em SQLite.
"""

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent / "data" / "stoken.db"
_lock = threading.RLock()  # reentrant — permite chamadas aninhadas


@contextmanager
def _db():
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _init_db():
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, _db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS interviews (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                interviewer TEXT    NOT NULL DEFAULT '',
                interviewee TEXT    NOT NULL DEFAULT '',
                role        TEXT    DEFAULT '',
                department  TEXT    DEFAULT '',
                level       TEXT    DEFAULT '',
                pillar      TEXT    DEFAULT '',
                date        TEXT    DEFAULT '',
                transcript  TEXT    DEFAULT '',
                ia_ready    INTEGER DEFAULT 0,
                created_at  TEXT    NOT NULL,
                analysis    TEXT
            );

            CREATE TABLE IF NOT EXISTS analysis_results (
                key          TEXT PRIMARY KEY,
                content      TEXT NOT NULL,
                generated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS insights (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                data         TEXT    NOT NULL,
                generated_at TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS diagnostic_scores (
                key   TEXT PRIMARY KEY,
                value REAL
            );

            INSERT OR IGNORE INTO diagnostic_scores (key, value) VALUES
                ('geral',      NULL),
                ('processos',  NULL),
                ('sistemas',   NULL),
                ('operacoes',  NULL),
                ('organizacao',NULL),
                ('roadmap',    NULL);

            CREATE TABLE IF NOT EXISTS pipeline_status (
                id              INTEGER PRIMARY KEY CHECK (id = 1),
                running         INTEGER DEFAULT 0,
                last_run        TEXT,
                steps_completed TEXT    DEFAULT '[]',
                errors          TEXT    DEFAULT '[]'
            );

            INSERT OR IGNORE INTO pipeline_status (id, running, steps_completed, errors)
            VALUES (1, 0, '[]', '[]');
        """)


_init_db()


# ─── Interviews ───────────────────────────────────────────────────────────────

def _row_to_interview(row) -> dict:
    return {
        "id":          row["id"],
        "interviewer": row["interviewer"],
        "interviewee": row["interviewee"],
        "role":        row["role"],
        "department":  row["department"],
        "level":       row["level"],
        "pillar":      row["pillar"],
        "date":        row["date"],
        "transcript":  row["transcript"],
        "ia_ready":    bool(row["ia_ready"]),
        "created_at":  row["created_at"],
        "analysis":    row["analysis"],
    }


def save_interview(data: dict) -> dict:
    now = datetime.now().isoformat()
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    with _lock, _db() as conn:
        cur = conn.execute(
            """INSERT INTO interviews
               (interviewer, interviewee, role, department, level, pillar,
                date, transcript, ia_ready, created_at, analysis)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data.get("interviewer", ""),
                data.get("interviewee", ""),
                data.get("role", ""),
                data.get("department", ""),
                data.get("level", ""),
                data.get("pillar", ""),
                date,
                data.get("transcript", ""),
                1 if data.get("ia_ready") else 0,
                now,
                None,
            ),
        )
        interview_id = cur.lastrowid

    interview = {
        "id":          interview_id,
        "interviewer": data.get("interviewer", ""),
        "interviewee": data.get("interviewee", ""),
        "role":        data.get("role", ""),
        "department":  data.get("department", ""),
        "level":       data.get("level", ""),
        "pillar":      data.get("pillar", ""),
        "date":        date,
        "transcript":  data.get("transcript", ""),
        "ia_ready":    bool(data.get("ia_ready")),
        "created_at":  now,
        "analysis":    None,
    }
    logger.info(f"Interview #{interview_id} saved: {interview['interviewee']}")
    return interview


def get_interviews() -> list:
    with _lock, _db() as conn:
        rows = conn.execute("SELECT * FROM interviews ORDER BY id").fetchall()
    return [_row_to_interview(r) for r in rows]


def get_interview(interview_id: int) -> Optional[dict]:
    with _lock, _db() as conn:
        row = conn.execute(
            "SELECT * FROM interviews WHERE id = ?", (interview_id,)
        ).fetchone()
    return _row_to_interview(row) if row else None


def update_interview_analysis(interview_id: int, analysis: str):
    with _lock, _db() as conn:
        conn.execute(
            "UPDATE interviews SET analysis = ? WHERE id = ?",
            (analysis, interview_id),
        )


# ─── Diagnostic Scores ────────────────────────────────────────────────────────

def set_diagnostic_scores(scores: dict):
    with _lock, _db() as conn:
        for key, value in scores.items():
            if isinstance(value, (int, float)):
                conn.execute(
                    "INSERT OR REPLACE INTO diagnostic_scores (key, value) VALUES (?,?)",
                    (key, float(value)),
                )
    logger.info(f"Diagnostic scores updated: {scores}")


def get_diagnostic_scores() -> dict:
    with _lock, _db() as conn:
        rows = conn.execute(
            "SELECT key, value FROM diagnostic_scores"
        ).fetchall()
    return {r["key"]: r["value"] for r in rows}


# ─── Analysis Results ─────────────────────────────────────────────────────────

def set_analysis_result(key: str, result: str):
    now = datetime.now().isoformat()
    with _lock, _db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO analysis_results (key, content, generated_at) VALUES (?,?,?)",
            (key, result, now),
        )


def get_analysis_results() -> dict:
    with _lock, _db() as conn:
        rows = conn.execute(
            "SELECT key, content, generated_at FROM analysis_results"
        ).fetchall()
    return {
        r["key"]: {"content": r["content"], "generated_at": r["generated_at"]}
        for r in rows
    }


# ─── Insights ─────────────────────────────────────────────────────────────────

def add_insight(insight: dict):
    now = datetime.now().isoformat()
    with _lock, _db() as conn:
        cur = conn.execute(
            "INSERT INTO insights (data, generated_at) VALUES (?,?)",
            (json.dumps(insight, ensure_ascii=False), now),
        )
        insight["id"] = cur.lastrowid
    insight["generated_at"] = now


def set_insights(insights: list):
    now = datetime.now().isoformat()
    with _lock, _db() as conn:
        conn.execute("DELETE FROM insights")
        for ins in insights:
            cur = conn.execute(
                "INSERT INTO insights (data, generated_at) VALUES (?,?)",
                (json.dumps(ins, ensure_ascii=False), now),
            )
            ins["id"] = cur.lastrowid
            ins["generated_at"] = now


def get_insights() -> list:
    with _lock, _db() as conn:
        rows = conn.execute(
            "SELECT id, data, generated_at FROM insights ORDER BY id"
        ).fetchall()
    result = []
    for row in rows:
        ins = json.loads(row["data"])
        ins["id"] = row["id"]
        ins["generated_at"] = row["generated_at"]
        result.append(ins)
    return result


# ─── Pipeline Status ──────────────────────────────────────────────────────────

def get_pipeline_status() -> dict:
    with _lock, _db() as conn:
        row = conn.execute(
            "SELECT * FROM pipeline_status WHERE id = 1"
        ).fetchone()
    if not row:
        return {"running": False, "last_run": None, "steps_completed": [], "errors": []}
    return {
        "running":         bool(row["running"]),
        "last_run":        row["last_run"],
        "steps_completed": json.loads(row["steps_completed"]),
        "errors":          json.loads(row["errors"]),
    }


def update_pipeline_status(running: bool = None, step: str = None, error: str = None):
    status = get_pipeline_status()
    if running is not None:
        status["running"] = running
        if running:
            status["steps_completed"] = []
            status["errors"] = []
    if step:
        status["steps_completed"].append(step)
    if error:
        status["errors"].append(error)
    if running is False:
        status["last_run"] = datetime.now().isoformat()

    with _lock, _db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO pipeline_status
               (id, running, last_run, steps_completed, errors)
               VALUES (1, ?, ?, ?, ?)""",
            (
                1 if status["running"] else 0,
                status["last_run"],
                json.dumps(status["steps_completed"]),
                json.dumps(status["errors"]),
            ),
        )

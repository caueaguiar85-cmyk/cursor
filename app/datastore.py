"""
Stoken Advisory — Database-backed Data Store
Persiste entrevistas, resultados de análise e insights em PostgreSQL (Railway).
"""

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


@contextmanager
def _db():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _init_db():
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set — database features disabled")
        return
    with _db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS interviews (
                id          SERIAL PRIMARY KEY,
                interviewer TEXT    NOT NULL DEFAULT '',
                interviewee TEXT    NOT NULL DEFAULT '',
                role        TEXT    DEFAULT '',
                department  TEXT    DEFAULT '',
                level       TEXT    DEFAULT '',
                pillar      TEXT    DEFAULT '',
                date        TEXT    DEFAULT '',
                transcript  TEXT    DEFAULT '',
                ia_ready    BOOLEAN DEFAULT FALSE,
                created_at  TEXT    NOT NULL,
                analysis    TEXT
            );

            CREATE TABLE IF NOT EXISTS analysis_results (
                key          TEXT PRIMARY KEY,
                content      TEXT NOT NULL,
                generated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS insights (
                id           SERIAL PRIMARY KEY,
                data         TEXT    NOT NULL,
                generated_at TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS diagnostic_scores (
                key   TEXT PRIMARY KEY,
                value DOUBLE PRECISION
            );

            CREATE TABLE IF NOT EXISTS pipeline_status (
                id              INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                running         BOOLEAN DEFAULT FALSE,
                last_run        TEXT,
                steps_completed TEXT    DEFAULT '[]',
                errors          TEXT    DEFAULT '[]'
            );
        """)

        # Seed default scores if empty
        cur.execute("SELECT COUNT(*) FROM diagnostic_scores")
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO diagnostic_scores (key, value) VALUES
                    ('geral',       NULL),
                    ('processos',   NULL),
                    ('sistemas',    NULL),
                    ('operacoes',   NULL),
                    ('organizacao', NULL),
                    ('roadmap',     NULL)
            """)

        # Seed pipeline_status if empty
        cur.execute("SELECT COUNT(*) FROM pipeline_status")
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO pipeline_status (id, running, steps_completed, errors)
                VALUES (1, FALSE, '[]', '[]')
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
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """INSERT INTO interviews
               (interviewer, interviewee, role, department, level, pillar,
                date, transcript, ia_ready, created_at, analysis)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING id""",
            (
                data.get("interviewer", ""),
                data.get("interviewee", ""),
                data.get("role", ""),
                data.get("department", ""),
                data.get("level", ""),
                data.get("pillar", ""),
                date,
                data.get("transcript", ""),
                bool(data.get("ia_ready")),
                now,
                None,
            ),
        )
        interview_id = cur.fetchone()["id"]

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
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM interviews ORDER BY id")
        rows = cur.fetchall()
    return [_row_to_interview(r) for r in rows]


def get_interview(interview_id: int) -> Optional[dict]:
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM interviews WHERE id = %s", (interview_id,))
        row = cur.fetchone()
    return _row_to_interview(row) if row else None


def update_interview_analysis(interview_id: int, analysis: str):
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE interviews SET analysis = %s WHERE id = %s",
            (analysis, interview_id),
        )


# ─── Diagnostic Scores ────────────────────────────────────────────────────────

def set_diagnostic_scores(scores: dict):
    with _db() as conn:
        cur = conn.cursor()
        for key, value in scores.items():
            if isinstance(value, (int, float)):
                cur.execute(
                    """INSERT INTO diagnostic_scores (key, value) VALUES (%s, %s)
                       ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
                    (key, float(value)),
                )
    logger.info(f"Diagnostic scores updated: {scores}")


def get_diagnostic_scores() -> dict:
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT key, value FROM diagnostic_scores")
        rows = cur.fetchall()
    return {r["key"]: r["value"] for r in rows}


# ─── Analysis Results ─────────────────────────────────────────────────────────

def set_analysis_result(key: str, result: str):
    now = datetime.now().isoformat()
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO analysis_results (key, content, generated_at) VALUES (%s, %s, %s)
               ON CONFLICT (key) DO UPDATE SET content = EXCLUDED.content, generated_at = EXCLUDED.generated_at""",
            (key, result, now),
        )


def get_analysis_results() -> dict:
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT key, content, generated_at FROM analysis_results")
        rows = cur.fetchall()
    return {
        r["key"]: {"content": r["content"], "generated_at": r["generated_at"]}
        for r in rows
    }


# ─── Insights ─────────────────────────────────────────────────────────────────

def add_insight(insight: dict):
    now = datetime.now().isoformat()
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "INSERT INTO insights (data, generated_at) VALUES (%s, %s) RETURNING id",
            (json.dumps(insight, ensure_ascii=False), now),
        )
        insight["id"] = cur.fetchone()["id"]
    insight["generated_at"] = now


def set_insights(insights: list):
    now = datetime.now().isoformat()
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("DELETE FROM insights")
        for ins in insights:
            cur.execute(
                "INSERT INTO insights (data, generated_at) VALUES (%s, %s) RETURNING id",
                (json.dumps(ins, ensure_ascii=False), now),
            )
            ins["id"] = cur.fetchone()["id"]
            ins["generated_at"] = now


def get_insights() -> list:
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, data, generated_at FROM insights ORDER BY id")
        rows = cur.fetchall()
    result = []
    for row in rows:
        ins = json.loads(row["data"])
        ins["id"] = row["id"]
        ins["generated_at"] = row["generated_at"]
        result.append(ins)
    return result


# ─── Pipeline Status ──────────────────────────────────────────────────────────

def get_pipeline_status() -> dict:
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM pipeline_status WHERE id = 1")
        row = cur.fetchone()
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

    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO pipeline_status (id, running, last_run, steps_completed, errors)
               VALUES (1, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET
                   running = EXCLUDED.running,
                   last_run = EXCLUDED.last_run,
                   steps_completed = EXCLUDED.steps_completed,
                   errors = EXCLUDED.errors""",
            (
                status["running"],
                status["last_run"],
                json.dumps(status["steps_completed"]),
                json.dumps(status["errors"]),
            ),
        )

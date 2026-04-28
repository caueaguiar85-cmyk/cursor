"""
Stoken Advisory — Database-backed Data Store
Persiste entrevistas, resultados de análise e insights em PostgreSQL (Railway).
Fallback gracioso quando DATABASE_URL não está configurado.
"""

import json
import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import psycopg2
    import psycopg2.extras
    _psycopg2_available = True
except ImportError:
    _psycopg2_available = False
    logger.warning("psycopg2 not installed — using in-memory fallback")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
_db_available = False

# ─── In-memory fallback (usado quando PostgreSQL não está disponível) ─────────
_mem_interviews = []
_mem_analysis_results = {}
_mem_insights = []
_mem_diagnostic_scores = {
    "geral": None, "processos": None, "sistemas": None,
    "operacoes": None, "organizacao": None, "roadmap": None,
}
_mem_pipeline_status = {
    "running": False, "last_run": None, "steps_completed": [], "errors": [],
}


@contextmanager
def _db():
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _init_db():
    global _db_available
    if not _psycopg2_available or not DATABASE_URL:
        logger.warning("Database not available — using in-memory fallback")
        return
    try:
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

        _db_available = True
        logger.info("PostgreSQL database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e} — using in-memory fallback")
        _db_available = False


# Init DB with timeout to avoid blocking app startup
def _safe_init():
    t = threading.Thread(target=_init_db, daemon=True)
    t.start()
    t.join(timeout=10)
    if t.is_alive():
        logger.warning("DB init timed out — using in-memory fallback")

_safe_init()


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

    if _db_available:
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
    else:
        interview_id = len(_mem_interviews) + 1

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
    if not _db_available:
        _mem_interviews.append(interview)
    logger.info(f"Interview #{interview_id} saved: {interview['interviewee']}")
    return interview


def get_interviews() -> list:
    if not _db_available:
        return _mem_interviews
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM interviews ORDER BY id")
        rows = cur.fetchall()
    return [_row_to_interview(r) for r in rows]


def get_interview(interview_id: int) -> Optional[dict]:
    if not _db_available:
        for i in _mem_interviews:
            if i["id"] == interview_id:
                return i
        return None
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM interviews WHERE id = %s", (interview_id,))
        row = cur.fetchone()
    return _row_to_interview(row) if row else None


def update_interview(interview_id: int, data: dict) -> Optional[dict]:
    """Atualiza campos de uma entrevista existente."""
    fields = ["interviewer", "interviewee", "role", "department", "level",
              "pillar", "date", "transcript", "ia_ready"]
    updates = {k: v for k, v in data.items() if k in fields}
    if not updates:
        return get_interview(interview_id)

    if not _db_available:
        for i in _mem_interviews:
            if i["id"] == interview_id:
                i.update(updates)
                return i
        return None

    set_clauses = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values())
    values.append(interview_id)
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE interviews SET {set_clauses} WHERE id = %s", values)
    return get_interview(interview_id)


def delete_interview(interview_id: int) -> bool:
    """Remove uma entrevista. Retorna True se encontrou e removeu."""
    if not _db_available:
        for i, iv in enumerate(_mem_interviews):
            if iv["id"] == interview_id:
                _mem_interviews.pop(i)
                return True
        return False
    with _db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM interviews WHERE id = %s RETURNING id", (interview_id,))
        return cur.fetchone() is not None


def update_interview_analysis(interview_id: int, analysis: str):
    if not _db_available:
        for i in _mem_interviews:
            if i["id"] == interview_id:
                i["analysis"] = analysis
                break
        return
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE interviews SET analysis = %s WHERE id = %s",
            (analysis, interview_id),
        )


# ─── Diagnostic Scores ────────────────────────────────────────────────────────

def set_diagnostic_scores(scores: dict):
    if not _db_available:
        _mem_diagnostic_scores.update(scores)
        return
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
    if not _db_available:
        return _mem_diagnostic_scores
    with _db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT key, value FROM diagnostic_scores")
        rows = cur.fetchall()
    return {r["key"]: r["value"] for r in rows}


# ─── Analysis Results ─────────────────────────────────────────────────────────

def set_analysis_result(key: str, result: str):
    now = datetime.now().isoformat()
    if not _db_available:
        _mem_analysis_results[key] = {"content": result, "generated_at": now}
        return
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO analysis_results (key, content, generated_at) VALUES (%s, %s, %s)
               ON CONFLICT (key) DO UPDATE SET content = EXCLUDED.content, generated_at = EXCLUDED.generated_at""",
            (key, result, now),
        )


def get_analysis_results() -> dict:
    if not _db_available:
        return _mem_analysis_results
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
    if not _db_available:
        insight["id"] = len(_mem_insights) + 1
        insight["generated_at"] = now
        _mem_insights.append(insight)
        return
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
    if not _db_available:
        global _mem_insights
        _mem_insights = insights
        for i, ins in enumerate(_mem_insights):
            ins["id"] = i + 1
            ins["generated_at"] = now
        return
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
    if not _db_available:
        return _mem_insights
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
    if not _db_available:
        return _mem_pipeline_status
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

    if not _db_available:
        _mem_pipeline_status.update(status)
        return

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

"""
Stoken Advisory — Database-backed Data Store
Persiste dados no PostgreSQL via DATABASE_URL (Railway).
Fallback in-memory quando não configurado.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Postgres connection ────────────────────────────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require" if "?" not in DATABASE_URL else "&sslmode=require"
_conn = None
_db_available = False

print(f"[DATASTORE] DATABASE_URL set: {bool(DATABASE_URL)} | len={len(DATABASE_URL)}", flush=True)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS interviews (
    id SERIAL PRIMARY KEY,
    interviewer TEXT DEFAULT '',
    interviewee TEXT DEFAULT '',
    role TEXT DEFAULT '',
    department TEXT DEFAULT '',
    level TEXT DEFAULT '',
    pillar TEXT DEFAULT '',
    date TEXT DEFAULT '',
    transcript TEXT DEFAULT '',
    ia_ready BOOLEAN DEFAULT FALSE,
    created_at TEXT DEFAULT '',
    analysis TEXT
);

CREATE TABLE IF NOT EXISTS diagnostic_scores (
    key TEXT PRIMARY KEY,
    value DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS analysis_results (
    key TEXT PRIMARY KEY,
    content TEXT,
    generated_at TEXT
);

CREATE TABLE IF NOT EXISTS insights (
    id SERIAL PRIMARY KEY,
    data TEXT,
    generated_at TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_status (
    id INTEGER PRIMARY KEY DEFAULT 1,
    running BOOLEAN DEFAULT FALSE,
    last_run TEXT,
    steps_completed TEXT DEFAULT '[]',
    errors TEXT DEFAULT '[]'
);
"""


def _get_conn():
    global _conn
    if _conn and not _conn.closed:
        return _conn
    try:
        _conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        _conn.autocommit = True
        return _conn
    except Exception as e:
        logger.error(f"Postgres reconnect failed: {e}")
        _conn = None
        return None


def _query(sql, params=None, fetch=True):
    """Execute a query, reconnecting once on failure."""
    conn = _get_conn()
    if not conn:
        return [] if fetch else None
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch:
                return [dict(r) for r in cur.fetchall()]
    except psycopg2.OperationalError:
        logger.warning("Postgres connection lost, reconnecting...")
        global _conn
        _conn = None
        conn = _get_conn()
        if not conn:
            return [] if fetch else None
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch:
                return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.error(f"Query error: {e}")
        return [] if fetch else None


if DATABASE_URL:
    print(f"[DATASTORE] Connecting to: {DATABASE_URL[:50]}...", flush=True)
    try:
        _conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        _conn.autocommit = True
        with _conn.cursor() as cur:
            cur.execute(_SCHEMA)
        _db_available = True
        print("[DATASTORE] PostgreSQL connected and tables ready", flush=True)
    except Exception as e:
        print(f"[DATASTORE] Postgres init error: {e}", flush=True)
        _conn = None
else:
    print("[DATASTORE] DATABASE_URL not set — in-memory fallback", flush=True)


# ─── In-memory fallback ──────────────────────────────────────────────────────
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


# ─── Interviews ───────────────────────────────────────────────────────────────

def save_interview(data: dict) -> dict:
    now = datetime.now().isoformat()
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    row = {
        "interviewer": data.get("interviewer", ""),
        "interviewee": data.get("interviewee", ""),
        "role": data.get("role", ""),
        "department": data.get("department", ""),
        "level": data.get("level", ""),
        "pillar": data.get("pillar", ""),
        "date": date,
        "transcript": data.get("transcript", ""),
        "ia_ready": bool(data.get("ia_ready")),
        "created_at": now,
        "analysis": None,
    }
    if _db_available:
        try:
            rows = _query(
                """INSERT INTO interviews (interviewer, interviewee, role, department, level, pillar, date, transcript, ia_ready, created_at, analysis)
                   VALUES (%(interviewer)s, %(interviewee)s, %(role)s, %(department)s, %(level)s, %(pillar)s, %(date)s, %(transcript)s, %(ia_ready)s, %(created_at)s, %(analysis)s)
                   RETURNING *""", row)
            if rows:
                row = rows[0]
        except Exception as e:
            logger.error(f"Save interview error: {e}")
            row["id"] = len(_mem_interviews) + 1
            _mem_interviews.append(row)
    else:
        row["id"] = len(_mem_interviews) + 1
        _mem_interviews.append(row)
    logger.info(f"Interview #{row.get('id')} saved: {row['interviewee']}")
    return row


def get_interviews() -> list:
    if not _db_available:
        return _mem_interviews
    try:
        return _query("SELECT * FROM interviews ORDER BY id")
    except Exception as e:
        logger.error(f"Get interviews error: {e}")
        return _mem_interviews


def get_interview(interview_id: int) -> Optional[dict]:
    if not _db_available:
        return next((i for i in _mem_interviews if i["id"] == interview_id), None)
    try:
        rows = _query("SELECT * FROM interviews WHERE id = %s", (interview_id,))
        return rows[0] if rows else None
    except Exception as e:
        logger.error(f"Get interview error: {e}")
        return None


def update_interview(interview_id: int, data: dict) -> Optional[dict]:
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
    try:
        set_clause = ", ".join(f"{k} = %({k})s" for k in updates)
        updates["id"] = interview_id
        rows = _query(f"UPDATE interviews SET {set_clause} WHERE id = %(id)s RETURNING *", updates)
        return rows[0] if rows else None
    except Exception as e:
        logger.error(f"Update interview error: {e}")
        return None


def delete_interview(interview_id: int) -> bool:
    if not _db_available:
        for i, iv in enumerate(_mem_interviews):
            if iv["id"] == interview_id:
                _mem_interviews.pop(i)
                return True
        return False
    try:
        rows = _query("DELETE FROM interviews WHERE id = %s RETURNING id", (interview_id,))
        return len(rows) > 0
    except Exception as e:
        logger.error(f"Delete interview error: {e}")
        return False


def update_interview_analysis(interview_id: int, analysis: str):
    if not _db_available:
        for i in _mem_interviews:
            if i["id"] == interview_id:
                i["analysis"] = analysis
                break
        return
    try:
        _query("UPDATE interviews SET analysis = %s WHERE id = %s", (analysis, interview_id), fetch=False)
    except Exception as e:
        logger.error(f"Update analysis error: {e}")


# ─── Diagnostic Scores ────────────────────────────────────────────────────────

def set_diagnostic_scores(scores: dict):
    if not _db_available:
        _mem_diagnostic_scores.update(scores)
        return
    try:
        for key, value in scores.items():
            if isinstance(value, (int, float)):
                _query(
                    """INSERT INTO diagnostic_scores (key, value) VALUES (%s, %s)
                       ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
                    (key, float(value)), fetch=False)
        logger.info(f"Diagnostic scores updated: {scores}")
    except Exception as e:
        logger.error(f"Set scores error: {e}")


def get_diagnostic_scores() -> dict:
    if not _db_available:
        return _mem_diagnostic_scores
    try:
        rows = _query("SELECT key, value FROM diagnostic_scores")
        return {r["key"]: r["value"] for r in rows}
    except Exception as e:
        logger.error(f"Get scores error: {e}")
        return _mem_diagnostic_scores


# ─── Analysis Results ─────────────────────────────────────────────────────────

def set_analysis_result(key: str, result: str):
    now = datetime.now().isoformat()
    if not _db_available:
        _mem_analysis_results[key] = {"content": result, "generated_at": now}
        return
    try:
        _query(
            """INSERT INTO analysis_results (key, content, generated_at) VALUES (%s, %s, %s)
               ON CONFLICT (key) DO UPDATE SET content = EXCLUDED.content, generated_at = EXCLUDED.generated_at""",
            (key, result, now), fetch=False)
    except Exception as e:
        logger.error(f"Set analysis error: {e}")


def get_analysis_results() -> dict:
    if not _db_available:
        return _mem_analysis_results
    try:
        rows = _query("SELECT key, content, generated_at FROM analysis_results")
        return {r["key"]: {"content": r["content"], "generated_at": r["generated_at"]} for r in rows}
    except Exception as e:
        logger.error(f"Get analysis error: {e}")
        return _mem_analysis_results


# ─── Per-Area Storage ─────────────────────────────────────────────────────────

def set_analysis_result_for_area(area: str, key: str, result: str):
    set_analysis_result(f"{key}:{area}", result)


def get_analysis_results_for_area(area: str) -> dict:
    suffix = f":{area}"
    if not _db_available:
        return {k.rsplit(":", 1)[0]: v for k, v in _mem_analysis_results.items() if k.endswith(suffix)}
    try:
        rows = _query("SELECT key, content, generated_at FROM analysis_results WHERE key LIKE %s",
                       (f"%{suffix}",))
        return {r["key"].rsplit(":", 1)[0]: {"content": r["content"], "generated_at": r["generated_at"]} for r in rows}
    except Exception as e:
        logger.error(f"Get area analysis error: {e}")
        return {}


def set_diagnostic_scores_for_area(area: str, scores: dict):
    if not _db_available:
        for key, value in scores.items():
            if isinstance(value, (int, float)):
                _mem_diagnostic_scores[f"{key}:{area}"] = value
        return
    try:
        for key, value in scores.items():
            if isinstance(value, (int, float)):
                _query(
                    """INSERT INTO diagnostic_scores (key, value) VALUES (%s, %s)
                       ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
                    (f"{key}:{area}", float(value)), fetch=False)
    except Exception as e:
        logger.error(f"Set area scores error: {e}")


def get_diagnostic_scores_for_area(area: str) -> dict:
    suffix = f":{area}"
    if not _db_available:
        return {k.rsplit(":", 1)[0]: v for k, v in _mem_diagnostic_scores.items() if k.endswith(suffix)}
    try:
        rows = _query("SELECT key, value FROM diagnostic_scores WHERE key LIKE %s", (f"%{suffix}",))
        return {r["key"].rsplit(":", 1)[0]: r["value"] for r in rows}
    except Exception as e:
        logger.error(f"Get area scores error: {e}")
        return {}


def get_available_diagnostic_areas() -> list:
    if not _db_available:
        areas = set()
        for k in _mem_analysis_results:
            if ":" in k:
                areas.add(k.rsplit(":", 1)[1])
        return sorted(areas)
    try:
        rows = _query("SELECT DISTINCT split_part(key, ':', 2) AS area FROM analysis_results WHERE key LIKE '%:%'")
        return sorted(r["area"] for r in rows if r["area"])
    except Exception as e:
        logger.error(f"Get areas error: {e}")
        return []


# ─── Insights ─────────────────────────────────────────────────────────────────

def add_insight(insight: dict):
    now = datetime.now().isoformat()
    if not _db_available:
        insight["id"] = len(_mem_insights) + 1
        insight["generated_at"] = now
        _mem_insights.append(insight)
        return
    try:
        rows = _query(
            "INSERT INTO insights (data, generated_at) VALUES (%s, %s) RETURNING id",
            (json.dumps(insight, ensure_ascii=False), now))
        if rows:
            insight["id"] = rows[0]["id"]
            insight["generated_at"] = now
    except Exception as e:
        logger.error(f"Add insight error: {e}")


def set_insights(insights: list):
    now = datetime.now().isoformat()
    if not _db_available:
        global _mem_insights
        _mem_insights = insights
        for i, ins in enumerate(_mem_insights):
            ins["id"] = i + 1
            ins["generated_at"] = now
        return
    try:
        _query("DELETE FROM insights", fetch=False)
        for ins in insights:
            rows = _query(
                "INSERT INTO insights (data, generated_at) VALUES (%s, %s) RETURNING id",
                (json.dumps(ins, ensure_ascii=False), now))
            if rows:
                ins["id"] = rows[0]["id"]
                ins["generated_at"] = now
    except Exception as e:
        logger.error(f"Set insights error: {e}")


def get_insights() -> list:
    if not _db_available:
        return _mem_insights
    try:
        rows = _query("SELECT id, data, generated_at FROM insights ORDER BY id")
        out = []
        for row in rows:
            ins = json.loads(row["data"])
            ins["id"] = row["id"]
            ins["generated_at"] = row["generated_at"]
            out.append(ins)
        return out
    except Exception as e:
        logger.error(f"Get insights error: {e}")
        return _mem_insights


# ─── Pipeline Status ──────────────────────────────────────────────────────────

def get_pipeline_status() -> dict:
    if not _db_available:
        return _mem_pipeline_status
    try:
        rows = _query("SELECT * FROM pipeline_status WHERE id = 1")
        if not rows:
            return {"running": False, "last_run": None, "steps_completed": [], "errors": []}
        row = rows[0]
        sc = row["steps_completed"]
        er = row["errors"]
        return {
            "running": bool(row["running"]),
            "last_run": row["last_run"],
            "steps_completed": json.loads(sc) if isinstance(sc, str) else (sc or []),
            "errors": json.loads(er) if isinstance(er, str) else (er or []),
        }
    except Exception as e:
        logger.error(f"Get pipeline error: {e}")
        return _mem_pipeline_status


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
    try:
        _query(
            """INSERT INTO pipeline_status (id, running, last_run, steps_completed, errors)
               VALUES (1, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET running = EXCLUDED.running, last_run = EXCLUDED.last_run,
               steps_completed = EXCLUDED.steps_completed, errors = EXCLUDED.errors""",
            (status["running"], status["last_run"],
             json.dumps(status["steps_completed"]), json.dumps(status["errors"])),
            fetch=False)
    except Exception as e:
        logger.error(f"Update pipeline error: {e}")

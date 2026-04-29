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

CREATE TABLE IF NOT EXISTS analysis_results (
    key TEXT PRIMARY KEY,
    content TEXT,
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


def delete_interview(interview_id: int) -> Optional[dict]:
    """Remove uma entrevista e retorna seus dados (para reprocessamento), ou None se não encontrada."""
    if not _db_available:
        for i, iv in enumerate(_mem_interviews):
            if iv["id"] == interview_id:
                return _mem_interviews.pop(i)
        return None
    try:
        rows = _query("DELETE FROM interviews WHERE id = %s RETURNING *", (interview_id,))
        return rows[0] if rows else None
    except Exception as e:
        logger.error(f"Delete interview error: {e}")
        return None


def count_interviews_with_transcript(department: str) -> int:
    """Conta entrevistas com transcrição em uma área (query leve, sem carregar dados)."""
    if not _db_available:
        return sum(1 for i in _mem_interviews
                   if i.get("department") == department and i.get("transcript"))
    try:
        rows = _query(
            "SELECT COUNT(*) AS cnt FROM interviews WHERE department = %s AND transcript IS NOT NULL AND transcript != ''",
            (department,))
        return rows[0]["cnt"] if rows else 0
    except Exception as e:
        logger.error(f"Count interviews error: {e}")
        return 0


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


def delete_analysis_results_for_area(area: str):
    """Remove todos os resultados de análise de uma área específica."""
    suffix = f":{area}"
    if not _db_available:
        keys_to_remove = [k for k in _mem_analysis_results if k.endswith(suffix)]
        for k in keys_to_remove:
            del _mem_analysis_results[k]
        logger.info(f"[mem] Removed {len(keys_to_remove)} analysis results for area '{area}'")
        return
    try:
        _query("DELETE FROM analysis_results WHERE key LIKE %s", (f"%{suffix}",), fetch=False)
        logger.info(f"[db] Removed analysis results for area '{area}'")
    except Exception as e:
        logger.error(f"Delete area analysis error: {e}")


def get_available_areas() -> list:
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

"""
Stoken Advisory — Database-backed Data Store
Persiste entrevistas, resultados de análise e insights no Supabase (PostgreSQL).
Fallback gracioso para in-memory quando Supabase não está configurado.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Supabase Client ─────────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
_sb = None
_db_available = False

try:
    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        _sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Quick test — try to read from interviews
        _sb.table("interviews").select("id").limit(1).execute()
        _db_available = True
        logger.info(f"Supabase connected: {SUPABASE_URL}")
    else:
        logger.warning("SUPABASE_URL/SUPABASE_KEY not set — using in-memory fallback")
except Exception as e:
    logger.error(f"Supabase init failed: {e} — using in-memory fallback")
    _db_available = False

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
            result = _sb.table("interviews").insert(row).execute()
            row["id"] = result.data[0]["id"]
        except Exception as e:
            logger.error(f"Supabase insert interview error: {e}")
            row["id"] = len(_mem_interviews) + 1
            _mem_interviews.append(row)
    else:
        row["id"] = len(_mem_interviews) + 1
        _mem_interviews.append(row)

    logger.info(f"Interview #{row['id']} saved: {row['interviewee']}")
    return row


def get_interviews() -> list:
    if not _db_available:
        return _mem_interviews
    try:
        result = _sb.table("interviews").select("*").order("id").execute()
        return result.data
    except Exception as e:
        logger.error(f"Supabase get interviews error: {e}")
        return _mem_interviews


def get_interview(interview_id: int) -> Optional[dict]:
    if not _db_available:
        for i in _mem_interviews:
            if i["id"] == interview_id:
                return i
        return None
    try:
        result = _sb.table("interviews").select("*").eq("id", interview_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Supabase get interview error: {e}")
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
        _sb.table("interviews").update(updates).eq("id", interview_id).execute()
        return get_interview(interview_id)
    except Exception as e:
        logger.error(f"Supabase update interview error: {e}")
        return None


def delete_interview(interview_id: int) -> bool:
    if not _db_available:
        for i, iv in enumerate(_mem_interviews):
            if iv["id"] == interview_id:
                _mem_interviews.pop(i)
                return True
        return False
    try:
        result = _sb.table("interviews").delete().eq("id", interview_id).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Supabase delete interview error: {e}")
        return False


def update_interview_analysis(interview_id: int, analysis: str):
    if not _db_available:
        for i in _mem_interviews:
            if i["id"] == interview_id:
                i["analysis"] = analysis
                break
        return
    try:
        _sb.table("interviews").update({"analysis": analysis}).eq("id", interview_id).execute()
    except Exception as e:
        logger.error(f"Supabase update analysis error: {e}")


# ─── Diagnostic Scores ────────────────────────────────────────────────────────

def set_diagnostic_scores(scores: dict):
    if not _db_available:
        _mem_diagnostic_scores.update(scores)
        return
    try:
        for key, value in scores.items():
            if isinstance(value, (int, float)):
                _sb.table("diagnostic_scores").upsert(
                    {"key": key, "value": float(value)},
                ).execute()
        logger.info(f"Diagnostic scores updated: {scores}")
    except Exception as e:
        logger.error(f"Supabase set scores error: {e}")


def get_diagnostic_scores() -> dict:
    if not _db_available:
        return _mem_diagnostic_scores
    try:
        result = _sb.table("diagnostic_scores").select("key, value").execute()
        return {r["key"]: r["value"] for r in result.data}
    except Exception as e:
        logger.error(f"Supabase get scores error: {e}")
        return _mem_diagnostic_scores


# ─── Analysis Results ─────────────────────────────────────────────────────────

def set_analysis_result(key: str, result: str):
    now = datetime.now().isoformat()
    if not _db_available:
        _mem_analysis_results[key] = {"content": result, "generated_at": now}
        return
    try:
        _sb.table("analysis_results").upsert(
            {"key": key, "content": result, "generated_at": now},
        ).execute()
    except Exception as e:
        logger.error(f"Supabase set analysis error: {e}")


def get_analysis_results() -> dict:
    if not _db_available:
        return _mem_analysis_results
    try:
        result = _sb.table("analysis_results").select("key, content, generated_at").execute()
        return {
            r["key"]: {"content": r["content"], "generated_at": r["generated_at"]}
            for r in result.data
        }
    except Exception as e:
        logger.error(f"Supabase get analysis error: {e}")
        return _mem_analysis_results


# ─── Insights ─────────────────────────────────────────────────────────────────

def add_insight(insight: dict):
    now = datetime.now().isoformat()
    if not _db_available:
        insight["id"] = len(_mem_insights) + 1
        insight["generated_at"] = now
        _mem_insights.append(insight)
        return
    try:
        result = _sb.table("insights").insert(
            {"data": json.dumps(insight, ensure_ascii=False), "generated_at": now}
        ).execute()
        insight["id"] = result.data[0]["id"]
        insight["generated_at"] = now
    except Exception as e:
        logger.error(f"Supabase add insight error: {e}")


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
        _sb.table("insights").delete().neq("id", 0).execute()
        for ins in insights:
            result = _sb.table("insights").insert(
                {"data": json.dumps(ins, ensure_ascii=False), "generated_at": now}
            ).execute()
            ins["id"] = result.data[0]["id"]
            ins["generated_at"] = now
    except Exception as e:
        logger.error(f"Supabase set insights error: {e}")


def get_insights() -> list:
    if not _db_available:
        return _mem_insights
    try:
        result = _sb.table("insights").select("id, data, generated_at").order("id").execute()
        out = []
        for row in result.data:
            ins = json.loads(row["data"])
            ins["id"] = row["id"]
            ins["generated_at"] = row["generated_at"]
            out.append(ins)
        return out
    except Exception as e:
        logger.error(f"Supabase get insights error: {e}")
        return _mem_insights


# ─── Pipeline Status ──────────────────────────────────────────────────────────

def get_pipeline_status() -> dict:
    if not _db_available:
        return _mem_pipeline_status
    try:
        result = _sb.table("pipeline_status").select("*").eq("id", 1).execute()
        if not result.data:
            return {"running": False, "last_run": None, "steps_completed": [], "errors": []}
        row = result.data[0]
        return {
            "running": bool(row["running"]),
            "last_run": row["last_run"],
            "steps_completed": json.loads(row["steps_completed"]) if isinstance(row["steps_completed"], str) else row["steps_completed"],
            "errors": json.loads(row["errors"]) if isinstance(row["errors"], str) else row["errors"],
        }
    except Exception as e:
        logger.error(f"Supabase get pipeline error: {e}")
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
        _sb.table("pipeline_status").upsert({
            "id": 1,
            "running": status["running"],
            "last_run": status["last_run"],
            "steps_completed": json.dumps(status["steps_completed"]),
            "errors": json.dumps(status["errors"]),
        }).execute()
    except Exception as e:
        logger.error(f"Supabase update pipeline error: {e}")

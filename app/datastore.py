"""
Stoken Advisory — Database-backed Data Store
Persiste dados no Supabase via REST API (PostgREST).
Usa httpx (leve) em vez do SDK completo do Supabase.
Fallback in-memory quando não configurado.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ─── Supabase REST config ────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
_REST_URL = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ""
_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
} if SUPABASE_KEY else {}

_db_available = False

if _REST_URL and _HEADERS:
    try:
        r = httpx.get(f"{_REST_URL}/interviews?select=id&limit=1",
                      headers=_HEADERS, timeout=5)
        if r.status_code in (200, 206):
            _db_available = True
            logger.info(f"Supabase connected: {SUPABASE_URL}")
        else:
            logger.error(f"Supabase test failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        logger.error(f"Supabase connection error: {e}")
else:
    logger.warning("SUPABASE_URL/SUPABASE_KEY not set — in-memory fallback")


def _get(path: str, params: dict = None) -> list:
    r = httpx.get(f"{_REST_URL}/{path}", headers=_HEADERS, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _post(table: str, data: dict) -> dict:
    r = httpx.post(f"{_REST_URL}/{table}", headers=_HEADERS, json=data, timeout=10)
    r.raise_for_status()
    return r.json()[0] if r.json() else data


def _patch(table: str, match: dict, data: dict) -> list:
    params = {f"{k}": f"eq.{v}" for k, v in match.items()}
    r = httpx.patch(f"{_REST_URL}/{table}", headers=_HEADERS, params=params,
                    json=data, timeout=10)
    r.raise_for_status()
    return r.json()


def _delete(table: str, match: dict) -> list:
    params = {f"{k}": f"eq.{v}" for k, v in match.items()}
    r = httpx.delete(f"{_REST_URL}/{table}", headers=_HEADERS, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _upsert(table: str, data: dict) -> dict:
    h = {**_HEADERS, "Prefer": "return=representation,resolution=merge-duplicates"}
    r = httpx.post(f"{_REST_URL}/{table}", headers=h, json=data, timeout=10)
    r.raise_for_status()
    return r.json()[0] if r.json() else data


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
            result = _post("interviews", row)
            row = result
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
        return _get("interviews?order=id")
    except Exception as e:
        logger.error(f"Get interviews error: {e}")
        return _mem_interviews


def get_interview(interview_id: int) -> Optional[dict]:
    if not _db_available:
        return next((i for i in _mem_interviews if i["id"] == interview_id), None)
    try:
        rows = _get(f"interviews?id=eq.{interview_id}")
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
        rows = _patch("interviews", {"id": interview_id}, updates)
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
        rows = _delete("interviews", {"id": interview_id})
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
        _patch("interviews", {"id": interview_id}, {"analysis": analysis})
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
                _upsert("diagnostic_scores", {"key": key, "value": float(value)})
        logger.info(f"Diagnostic scores updated: {scores}")
    except Exception as e:
        logger.error(f"Set scores error: {e}")


def get_diagnostic_scores() -> dict:
    if not _db_available:
        return _mem_diagnostic_scores
    try:
        rows = _get("diagnostic_scores?select=key,value")
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
        _upsert("analysis_results", {"key": key, "content": result, "generated_at": now})
    except Exception as e:
        logger.error(f"Set analysis error: {e}")


def get_analysis_results() -> dict:
    if not _db_available:
        return _mem_analysis_results
    try:
        rows = _get("analysis_results?select=key,content,generated_at")
        return {r["key"]: {"content": r["content"], "generated_at": r["generated_at"]} for r in rows}
    except Exception as e:
        logger.error(f"Get analysis error: {e}")
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
        result = _post("insights", {"data": json.dumps(insight, ensure_ascii=False), "generated_at": now})
        insight["id"] = result["id"]
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
        # Delete all then insert
        httpx.delete(f"{_REST_URL}/insights?id=gt.0", headers=_HEADERS, timeout=10)
        for ins in insights:
            result = _post("insights", {"data": json.dumps(ins, ensure_ascii=False), "generated_at": now})
            ins["id"] = result["id"]
            ins["generated_at"] = now
    except Exception as e:
        logger.error(f"Set insights error: {e}")


def get_insights() -> list:
    if not _db_available:
        return _mem_insights
    try:
        rows = _get("insights?select=id,data,generated_at&order=id")
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
        rows = _get("pipeline_status?id=eq.1")
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
        _upsert("pipeline_status", {
            "id": 1,
            "running": status["running"],
            "last_run": status["last_run"],
            "steps_completed": json.dumps(status["steps_completed"]),
            "errors": json.dumps(status["errors"]),
        })
    except Exception as e:
        logger.error(f"Update pipeline error: {e}")

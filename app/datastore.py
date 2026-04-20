"""
Stoken Advisory — In-memory Data Store
Armazena entrevistas, resultados de análise e insights.
Em produção, substituir por PostgreSQL.
"""

import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ─── In-memory stores ─────────────────────────────────────────────────────────

_interviews = []
_analysis_results = {}  # pillar → analysis text
_insights = []
_diagnostic_scores = {
    "geral": None,
    "processos": None,
    "sistemas": None,
    "operacoes": None,
    "organizacao": None,
    "roadmap": None,
}
_pipeline_status = {
    "running": False,
    "last_run": None,
    "steps_completed": [],
    "errors": [],
}


# ─── Interviews ───────────────────────────────────────────────────────────────

def save_interview(data: dict) -> dict:
    """Salva uma entrevista no datastore."""
    interview = {
        "id": len(_interviews) + 1,
        "interviewer": data.get("interviewer", ""),
        "interviewee": data.get("interviewee", ""),
        "role": data.get("role", ""),
        "department": data.get("department", ""),
        "level": data.get("level", ""),
        "pillar": data.get("pillar", ""),
        "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "transcript": data.get("transcript", ""),
        "ia_ready": data.get("ia_ready", False),
        "created_at": datetime.now().isoformat(),
        "analysis": None,  # populated by PRISM
    }
    _interviews.append(interview)
    logger.info(f"Interview #{interview['id']} saved: {interview['interviewee']}")
    return interview


def get_interviews() -> list:
    return _interviews


def get_interview(interview_id: int) -> Optional[dict]:
    for i in _interviews:
        if i["id"] == interview_id:
            return i
    return None


def update_interview_analysis(interview_id: int, analysis: str):
    for i in _interviews:
        if i["id"] == interview_id:
            i["analysis"] = analysis
            break


# ─── Diagnostic Scores ────────────────────────────────────────────────────────

def set_diagnostic_scores(scores: dict):
    """scores = {"geral": 2.1, "processos": 1.8, ...}"""
    global _diagnostic_scores
    _diagnostic_scores.update(scores)
    logger.info(f"Diagnostic scores updated: {scores}")


def get_diagnostic_scores() -> dict:
    return _diagnostic_scores


# ─── Analysis Results ─────────────────────────────────────────────────────────

def set_analysis_result(key: str, result: str):
    _analysis_results[key] = {
        "content": result,
        "generated_at": datetime.now().isoformat(),
    }


def get_analysis_results() -> dict:
    return _analysis_results


# ─── Insights ─────────────────────────────────────────────────────────────────

def add_insight(insight: dict):
    insight["id"] = len(_insights) + 1
    insight["generated_at"] = datetime.now().isoformat()
    _insights.append(insight)


def set_insights(insights: list):
    global _insights
    _insights = insights
    for i, ins in enumerate(_insights):
        ins["id"] = i + 1
        ins["generated_at"] = datetime.now().isoformat()


def get_insights() -> list:
    return _insights


# ─── Pipeline Status ──────────────────────────────────────────────────────────

def get_pipeline_status() -> dict:
    return _pipeline_status


def update_pipeline_status(running: bool = None, step: str = None, error: str = None):
    if running is not None:
        _pipeline_status["running"] = running
        if running:
            _pipeline_status["steps_completed"] = []
            _pipeline_status["errors"] = []
    if step:
        _pipeline_status["steps_completed"].append(step)
    if error:
        _pipeline_status["errors"].append(error)
    if not running and running is not None:
        _pipeline_status["last_run"] = datetime.now().isoformat()

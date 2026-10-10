"""Tools the agent can call.

Every tool is a normal Python function. The registry below maps each tool to the
permission it needs, and execute_tool() checks that permission in code - the LLM
can only *suggest* a tool name, it cannot grant itself access.
Each tool returns {"data": ..., "text": optional narrative, "llm_used": bool}.
"""
from dataclasses import dataclass
from typing import Callable

from app.auth.permissions import check_permission
from app.exceptions import ValidationError
from app.services import analysis_service, candidate_service, job_service


def _int(value, name: str, low: int = 1, high: int = 10**9) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{name}' must be a whole number.")
    if not low <= number <= high:
        raise ValidationError(f"'{name}' must be between {low} and {high}.")
    return number


def search_candidates_tool(user: dict, query: str, top_k: int = 5) -> dict:
    results = candidate_service.search_candidates(query, top_k=_int(top_k, "top_k", 1, 10))
    return {"data": results, "text": None, "llm_used": False}


def get_candidate_details_tool(user: dict, candidate_id: int) -> dict:
    return {"data": candidate_service.get_candidate(_int(candidate_id, "candidate_id")),
            "text": None, "llm_used": False}


def analyze_job_tool(user: dict, job_id: int) -> dict:
    result = analysis_service.analyze_job(_int(job_id, "job_id"))
    return {"data": result, "text": result["summary"], "llm_used": result["llm_used"]}


def match_candidate_tool(user: dict, candidate_id: int, job_id: int) -> dict:
    result = analysis_service.match_candidate(_int(candidate_id, "candidate_id"), _int(job_id, "job_id"))
    return {"data": result, "text": result["explanation"], "llm_used": result["llm_used"]}


def compare_candidates_tool(user: dict, candidate_ids: list, job_id: int | None = None) -> dict:
    ids = [_int(i, "candidate_id") for i in candidate_ids]
    result = analysis_service.compare_candidates(ids, _int(job_id, "job_id") if job_id else None)
    return {"data": result, "text": result["comparison"], "llm_used": result["llm_used"]}


def generate_interview_questions_tool(user: dict, candidate_id: int, job_id: int | None = None,
                                      num_questions: int = 8) -> dict:
    result = analysis_service.generate_interview_questions(
        _int(candidate_id, "candidate_id"), _int(job_id, "job_id") if job_id else None,
        _int(num_questions, "num_questions", 3, 15))
    return {"data": result, "text": result["questions"], "llm_used": result["llm_used"]}


def summarize_candidate_tool(user: dict, candidate_id: int, job_id: int | None = None) -> dict:
    result = analysis_service.summarize_candidate(
        _int(candidate_id, "candidate_id"), _int(job_id, "job_id") if job_id else None)
    return {"data": result, "text": result["summary"], "llm_used": result["llm_used"]}


@dataclass
class ToolSpec:
    name: str
    description: str
    permission: str
    func: Callable
    allowed_args: tuple


TOOLS: dict[str, ToolSpec] = {t.name: t for t in [
    ToolSpec("search_candidates", "Find candidates matching a natural-language query (RAG over resumes).",
             "candidates:search", search_candidates_tool, ("query", "top_k")),
    ToolSpec("get_candidate_details", "Show stored details of one candidate by ID.",
             "candidates:read", get_candidate_details_tool, ("candidate_id",)),
    ToolSpec("analyze_job", "Analyse a job description: skills, seniority, summary.",
             "jobs:read", analyze_job_tool, ("job_id",)),
    ToolSpec("match_candidate", "Score how well one candidate fits one job.",
             "candidates:analyze", match_candidate_tool, ("candidate_id", "job_id")),
    ToolSpec("compare_candidates", "Compare 2-5 candidates, optionally against a job.",
             "candidates:analyze", compare_candidates_tool, ("candidate_ids", "job_id")),
    ToolSpec("generate_interview_questions", "Generate interview questions for a candidate (and job).",
             "candidates:analyze", generate_interview_questions_tool, ("candidate_id", "job_id", "num_questions")),
    ToolSpec("summarize_candidate", "Write a recruiter summary of a candidate.",
             "candidates:analyze", summarize_candidate_tool, ("candidate_id", "job_id")),
]}


def execute_tool(name: str, user: dict, args: dict) -> dict:
    """Validate the tool name, check permission in Python, then run it."""
    spec = TOOLS.get(name)
    if spec is None:
        raise ValidationError(f"Unknown tool '{name}'.")
    check_permission(user, spec.permission)  # deterministic authorization
    clean_args = {k: v for k, v in (args or {}).items() if k in spec.allowed_args}
    try:
        return spec.func(user, **clean_args)
    except TypeError as exc:
        raise ValidationError("Missing or invalid arguments for this request.") from exc

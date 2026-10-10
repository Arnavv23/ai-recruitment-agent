from fastapi import APIRouter, Depends

from app.auth.dependencies import require_permission
from app.models.schemas import CompareRequest, MatchRequest, QuestionsRequest, SummaryRequest
from app.services import analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])
_perm = require_permission("candidates:analyze")


@router.post("/match")
def match(body: MatchRequest, user: dict = Depends(_perm)):
    return analysis_service.match_candidate(body.candidate_id, body.job_id)


@router.post("/summary")
def summary(body: SummaryRequest, user: dict = Depends(_perm)):
    return analysis_service.summarize_candidate(body.candidate_id, body.job_id)


@router.post("/questions")
def questions(body: QuestionsRequest, user: dict = Depends(_perm)):
    return analysis_service.generate_interview_questions(body.candidate_id, body.job_id, body.num_questions)


@router.post("/compare")
def compare(body: CompareRequest, user: dict = Depends(_perm)):
    return analysis_service.compare_candidates(body.candidate_ids, body.job_id)


@router.get("/job/{job_id}")
def job_analysis(job_id: int, user: dict = Depends(require_permission("jobs:read"))):
    return analysis_service.analyze_job(job_id)

from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.utils import read_upload
from app.auth.dependencies import require_permission
from app.models.schemas import SearchRequest
from app.services import candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/upload", status_code=201)
def upload_resume(file: UploadFile = File(...), user: dict = Depends(require_permission("candidates:upload"))):
    data = read_upload(file, (".pdf",))
    return candidate_service.create_candidate_from_pdf(file.filename, data, user["username"])


@router.get("")
def list_candidates(skill: Optional[str] = None, user: dict = Depends(require_permission("candidates:read"))):
    return candidate_service.list_candidates(skill)


@router.post("/search")
def search(body: SearchRequest, user: dict = Depends(require_permission("candidates:search"))):
    results = candidate_service.search_candidates(body.query, body.top_k)
    return {"query": body.query, "count": len(results), "results": results,
            "message": None if results else "No matching candidates found."}


@router.get("/{candidate_id}")
def get_candidate(candidate_id: int, user: dict = Depends(require_permission("candidates:read"))):
    return candidate_service.get_candidate(candidate_id)


@router.delete("/{candidate_id}")
def delete_candidate(candidate_id: int, user: dict = Depends(require_permission("candidates:delete"))):
    candidate_service.delete_candidate(candidate_id, user["username"])
    return {"deleted": candidate_id}

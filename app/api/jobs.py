from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.utils import read_upload
from app.auth.dependencies import require_permission
from app.models.schemas import JobCreate
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", status_code=201)
def create_job(body: JobCreate, user: dict = Depends(require_permission("jobs:create"))):
    return job_service.create_job(body.title, body.description, user["username"], body.required_skills)


@router.post("/upload", status_code=201)
def upload_job(title: str = Form(...), file: UploadFile = File(...),
               user: dict = Depends(require_permission("jobs:create"))):
    data = read_upload(file, (".pdf", ".txt"))
    return job_service.create_job_from_file(title, file.filename, data, user["username"])


@router.get("")
def list_jobs(user: dict = Depends(require_permission("jobs:read"))):
    return job_service.list_jobs()


@router.get("/{job_id}")
def get_job(job_id: int, user: dict = Depends(require_permission("jobs:read"))):
    return job_service.get_job(job_id)


@router.delete("/{job_id}")
def delete_job(job_id: int, user: dict = Depends(require_permission("jobs:delete"))):
    job_service.delete_job(job_id, user["username"])
    return {"deleted": job_id}

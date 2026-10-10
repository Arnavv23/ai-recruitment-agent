from fastapi import APIRouter, Depends

from app.auth.dependencies import require_permission
from app.models.schemas import UserCreate
from app.services import candidate_service, user_service

router = APIRouter(tags=["admin"])


@router.get("/admin/users")
def list_users(user: dict = Depends(require_permission("users:manage"))):
    return user_service.list_users()


@router.post("/admin/users", status_code=201)
def create_user(body: UserCreate, user: dict = Depends(require_permission("users:manage"))):
    return user_service.create_user(body.username, body.password, body.role, actor=user["username"])


@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, user: dict = Depends(require_permission("users:manage"))):
    user_service.delete_user(user_id, user)
    return {"deleted": user_id}


@router.get("/admin/audit")
def audit_log(user: dict = Depends(require_permission("users:manage"))):
    return user_service.list_audit()


@router.get("/dashboard/stats")
def stats(user: dict = Depends(require_permission("candidates:read"))):
    return candidate_service.dashboard_stats()

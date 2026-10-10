"""Role-based access control. Plain Python - the LLM never touches this."""
from app.exceptions import PermissionDenied

RECRUITER_PERMISSIONS = {
    "jobs:create", "jobs:read",
    "candidates:upload", "candidates:read", "candidates:search", "candidates:analyze",
    "agent:query",
}
ADMIN_PERMISSIONS = RECRUITER_PERMISSIONS | {"candidates:delete", "jobs:delete", "users:manage"}

ROLE_PERMISSIONS = {
    "recruiter": RECRUITER_PERMISSIONS,
    "admin": ADMIN_PERMISSIONS,
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def check_permission(user: dict, permission: str) -> None:
    """Raise PermissionDenied unless the user's role grants the permission."""
    if not user or not has_permission(user.get("role", ""), permission):
        raise PermissionDenied("You do not have permission to perform this action.")

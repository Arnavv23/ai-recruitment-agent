"""FastAPI dependencies: who is calling, and are they allowed?"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.permissions import check_permission
from app.auth.security import decode_token
from app.exceptions import AuthError
from app.services.user_service import get_user_by_username

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
    if creds is None:
        raise AuthError("Missing authentication token.")
    payload = decode_token(creds.credentials)
    user = get_user_by_username(payload.get("sub", ""))
    if not user:
        raise AuthError("User no longer exists.")
    return user  # role comes from the database, not from the token


def require_permission(permission: str):
    """Use as: user = Depends(require_permission("candidates:delete"))"""
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        check_permission(user, permission)
        return user
    return dependency

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.security import create_token
from app.exceptions import AuthError
from app.models.schemas import LoginRequest
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest):
    user = user_service.authenticate(body.username, body.password)
    if not user:
        user_service.log_action(body.username[:64], "login_failed")
        raise AuthError("Incorrect username or password.")
    user_service.log_action(user["username"], "login")
    return {"access_token": create_token(user["username"]), "token_type": "bearer", "user": user}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user

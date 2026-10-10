from fastapi import APIRouter, Depends

from app.agents.graph import run_agent
from app.auth.dependencies import require_permission
from app.models.schemas import AgentQuery

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query")
def query_agent(body: AgentQuery, user: dict = Depends(require_permission("agent:query"))):
    return run_agent(user, body.query)

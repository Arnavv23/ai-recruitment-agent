"""Pydantic request models (input validation for the API)."""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserCreate(BaseModel):
    username: str
    password: str
    role: Literal["recruiter", "admin"] = "recruiter"


class JobCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=20, max_length=20000)
    required_skills: Optional[list[str]] = Field(default=None, max_length=50)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10)


class MatchRequest(BaseModel):
    candidate_id: int
    job_id: int


class SummaryRequest(BaseModel):
    candidate_id: int
    job_id: Optional[int] = None


class QuestionsRequest(BaseModel):
    candidate_id: int
    job_id: Optional[int] = None
    num_questions: int = Field(default=8, ge=3, le=15)


class CompareRequest(BaseModel):
    candidate_ids: list[int] = Field(min_length=2, max_length=5)
    job_id: Optional[int] = None


class AgentQuery(BaseModel):
    query: str = Field(min_length=1, max_length=1000)

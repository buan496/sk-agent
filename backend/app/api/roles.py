from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.repo import get_repo_reader
from app.config import Settings, get_settings
from app.roles.role_registry import role_metadata
from app.roles.role_router import RoleRouter, list_internal_role_runs
from app.services.repo_reader import RepoReader

router = APIRouter(prefix="/roles", tags=["roles"])


class RoleRunRequest(BaseModel):
    task_type: str = Field(..., min_length=1)
    input: str = Field(..., min_length=1)
    notes: str = ""
    preferred_role: str | None = None
    allow_web: bool = False
    web_queries: list[str] = Field(default_factory=list)


@router.get("")
def roles() -> dict:
    return {
        "status": "ok",
        "roles": role_metadata(),
    }


@router.post("/run")
def run_role(
    request: RoleRunRequest,
    settings: Settings = Depends(get_settings),
    reader: RepoReader = Depends(get_repo_reader),
) -> dict:
    try:
        return RoleRouter(settings=settings, reader=reader).run(
            task_type=request.task_type,
            user_input=request.input,
            notes=request.notes,
            preferred_role=request.preferred_role,
            allow_web=request.allow_web,
            web_queries=request.web_queries,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs")
def role_runs(limit: int = Query(default=10, ge=1, le=100)) -> dict:
    runs = list_internal_role_runs(limit=limit)
    return {
        "status": "ok",
        "count": len(runs),
        "runs": runs,
    }

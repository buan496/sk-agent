from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.repo import get_repo_reader
from app.cognitive.cognitive_session import sessions, state, think
from app.config import Settings, get_settings
from app.services.repo_reader import RepoReader

router = APIRouter(prefix="/cognitive", tags=["cognitive"])


class ThinkRequest(BaseModel):
    input: str = Field(..., min_length=1)
    session_id: str | None = None
    allow_web: bool = False
    read_sources: bool = False


@router.post("/think")
def cognitive_think(
    request: ThinkRequest,
    settings: Settings = Depends(get_settings),
    reader: RepoReader = Depends(get_repo_reader),
) -> dict:
    return think(
        settings=settings,
        reader=reader,
        user_input=request.input,
        session_id=request.session_id,
        allow_web=request.allow_web,
        read_sources=request.read_sources,
    )


@router.get("/sessions")
def cognitive_sessions(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    items = sessions(limit=limit)
    return {
        "status": "ok",
        "count": len(items),
        "sessions": items,
    }


@router.get("/sessions/{session_id}/state")
def cognitive_state(session_id: str) -> dict:
    result = state(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="cognitive_session_not_found")
    return {
        "status": "ok",
        **result,
    }

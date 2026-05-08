from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.web_search import search_web

router = APIRouter(prefix="/web", tags=["web"])


class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=10)


@router.post("/search")
def web_search(request: WebSearchRequest, settings: Settings = Depends(get_settings)) -> dict:
    return search_web(query=request.query, limit=request.limit, settings=settings)

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.source_reader import read_source
from app.services.web_search import search_web

router = APIRouter(prefix="/web", tags=["web"])


class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=10)


class SourceReadRequest(BaseModel):
    url: str = Field(..., min_length=1)
    source_type: str = "unknown"
    max_chars: int = Field(default=12000, ge=1000, le=50000)


@router.post("/search")
def web_search(request: WebSearchRequest, settings: Settings = Depends(get_settings)) -> dict:
    return search_web(query=request.query, limit=request.limit, settings=settings)


@router.post("/read-source")
def read_web_source(request: SourceReadRequest) -> dict:
    return read_source(
        url=request.url,
        source_type=request.source_type,
        max_chars=request.max_chars,
    )

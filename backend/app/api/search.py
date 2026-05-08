from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.repo import get_repo_reader
from app.config import Settings, get_settings
from app.services.canonical_preflight import canonical_preflight
from app.services.llm_client import LLMConfigurationError
from app.services.qa_service import QAService
from app.services.repo_reader import RepoReader
from app.services.retriever import Retriever

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=50)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    limit: int = Field(default=8, ge=1, le=20)


@router.post("/search")
def search(request: SearchRequest) -> dict:
    return Retriever().search(request.query, limit=request.limit)


@router.post("/ask")
def ask(
    request: AskRequest,
    settings: Settings = Depends(get_settings),
    reader: RepoReader = Depends(get_repo_reader),
) -> dict:
    try:
        preflight = canonical_preflight(reader)
        return QAService(settings=settings, reader=reader).ask(
            request.question,
            limit=request.limit,
            preflight=preflight,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

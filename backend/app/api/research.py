from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.research_state import (
    add_candidate_source,
    create_or_get_research_object,
    get_research_state,
    ingest_role_run,
    list_research_objects,
    read_source_into_state,
)

router = APIRouter(prefix="/research", tags=["research"])


class ResearchObjectRequest(BaseModel):
    name: str = Field(..., min_length=1)
    slug: str | None = None
    notes: str | None = None


class CandidateSourceRequest(BaseModel):
    url: str = Field(..., min_length=1)
    title: str = ""
    source_type: str = "unknown"
    source_reason: str = ""
    evidence_level: str | None = None


class ReadSourceRequest(CandidateSourceRequest):
    max_chars: int = Field(default=12000, ge=1000, le=50000)


class IngestRoleRunRequest(BaseModel):
    run_id: int = Field(..., ge=1)


@router.post("/objects")
def create_object(request: ResearchObjectRequest) -> dict:
    obj = create_or_get_research_object(name=request.name, slug=request.slug, notes=request.notes)
    return {
        "status": "ok",
        "object": obj,
    }


@router.get("/objects")
def objects(limit: int = Query(default=50, ge=1, le=100)) -> dict:
    items = list_research_objects(limit=limit)
    return {
        "status": "ok",
        "count": len(items),
        "objects": items,
    }


@router.get("/objects/{slug}/state")
def object_state(slug: str) -> dict:
    state = get_research_state(slug)
    if not state:
        raise HTTPException(status_code=404, detail="research_object_not_found")
    return {
        "status": "ok",
        "state": state,
    }


@router.post("/objects/{slug}/sources")
def add_source(slug: str, request: CandidateSourceRequest) -> dict:
    try:
        source = add_candidate_source(slug, request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "status": "ok",
        "source": source,
    }


@router.post("/objects/{slug}/read-source")
def read_source(slug: str, request: ReadSourceRequest) -> dict:
    try:
        result = read_source_into_state(slug, request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "status": "ok",
        **result,
    }


@router.post("/objects/{slug}/ingest-role-run")
def ingest_run(slug: str, request: IngestRoleRunRequest) -> dict:
    try:
        result = ingest_role_run(slug, request.run_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail.endswith("_not_found") else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "status": "ok",
        **result,
    }

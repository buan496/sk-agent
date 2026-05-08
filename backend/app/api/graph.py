from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.repo import get_repo_reader
from app.config import Settings, get_settings
from app.services.canonical_preflight import canonical_preflight
from app.services.graph_builder import GraphBuilder, GraphUnavailableError
from app.services.repo_reader import RepoReader

router = APIRouter(prefix="/graph", tags=["graph"])


def get_graph_builder(settings: Settings = Depends(get_settings)) -> GraphBuilder:
    return GraphBuilder(settings)


@router.post("/rebuild")
def rebuild_graph(builder: GraphBuilder = Depends(get_graph_builder)) -> dict:
    try:
        return builder.rebuild()
    except GraphUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/status")
def graph_status(
    builder: GraphBuilder = Depends(get_graph_builder),
    reader: RepoReader = Depends(get_repo_reader),
) -> dict:
    try:
        status = builder.status()
        preflight = canonical_preflight(reader)
        status["canonical_read_status"] = {
            "status": preflight.get("status"),
            "read_count": preflight.get("read_count"),
            "total": preflight.get("total"),
            "read_files": preflight.get("read_files", []),
        }
        return status
    except GraphUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/failure-modes/{code}/cases")
def cases_for_failure_mode(
    code: str,
    builder: GraphBuilder = Depends(get_graph_builder),
) -> dict:
    try:
        return builder.cases_for_failure_mode(code)
    except GraphUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/frameworks/articles")
def articles_for_framework(
    framework: str = Query(..., min_length=1),
    builder: GraphBuilder = Depends(get_graph_builder),
) -> dict:
    try:
        return builder.articles_for_framework(framework)
    except GraphUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/products/tools")
def tool_products(builder: GraphBuilder = Depends(get_graph_builder)) -> dict:
    try:
        return builder.tool_products()
    except GraphUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/theories/reused")
def reused_theories(
    min_cases: int = Query(default=2, ge=1, le=20),
    builder: GraphBuilder = Depends(get_graph_builder),
) -> dict:
    try:
        return builder.reused_theories(min_cases=min_cases)
    except GraphUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.repo import get_repo_reader
from app.config import Settings, get_settings
from app.services.repo_reader import RepoReader
from app.services.sk_workflow_agents import SKWorkflowAgents, WorkflowInput
from app.services.status_auditor import StatusAuditor

router = APIRouter(prefix="/agents", tags=["agents"])


class ProductTeardownRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    notes: str = ""
    limit: int = Field(default=8, ge=1, le=20)


class FrameworkRedTeamRequest(BaseModel):
    idea: str = Field(..., min_length=1)
    notes: str = ""
    limit: int = Field(default=8, ge=1, le=20)


class ArticlePublishCheckRequest(BaseModel):
    final_article: str = Field(..., min_length=1)
    notes: str = ""
    limit: int = Field(default=8, ge=1, le=20)


@router.post("/status-audit")
def status_audit(reader: RepoReader = Depends(get_repo_reader)) -> dict:
    return StatusAuditor(reader).audit()


@router.post("/product-teardown")
def product_teardown(
    request: ProductTeardownRequest,
    settings: Settings = Depends(get_settings),
    reader: RepoReader = Depends(get_repo_reader),
) -> dict:
    try:
        return SKWorkflowAgents(settings=settings, reader=reader).product_teardown(
            WorkflowInput(
                value=request.product_name,
                notes=request.notes,
                limit=request.limit,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/framework-red-team")
def framework_red_team(
    request: FrameworkRedTeamRequest,
    settings: Settings = Depends(get_settings),
    reader: RepoReader = Depends(get_repo_reader),
) -> dict:
    try:
        return SKWorkflowAgents(settings=settings, reader=reader).framework_red_team(
            WorkflowInput(
                value=request.idea,
                notes=request.notes,
                limit=request.limit,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/article-publish-check")
def article_publish_check(
    request: ArticlePublishCheckRequest,
    settings: Settings = Depends(get_settings),
    reader: RepoReader = Depends(get_repo_reader),
) -> dict:
    try:
        return SKWorkflowAgents(settings=settings, reader=reader).article_publish_check(
            WorkflowInput(
                value=request.final_article,
                notes=request.notes,
                limit=request.limit,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

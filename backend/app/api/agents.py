from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.repo import get_repo_reader
from app.services.repo_reader import RepoReader
from app.services.status_auditor import StatusAuditor

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/status-audit")
def status_audit(reader: RepoReader = Depends(get_repo_reader)) -> dict:
    return StatusAuditor(reader).audit()

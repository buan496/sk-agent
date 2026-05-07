from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.repo import get_repo_reader
from app.services.patch_writer import PatchDraftInput, PatchWriter
from app.services.repo_reader import RepoReader

router = APIRouter(prefix="/patch", tags=["patch"])


class PatchDraftRequest(BaseModel):
    target_file: str = Field(..., min_length=1)
    intent: str = Field(..., min_length=1)
    new_content: str = Field(..., min_length=1)
    operation: str = Field(default="auto")


@router.post("/draft")
def draft_patch(
    request: PatchDraftRequest,
    reader: RepoReader = Depends(get_repo_reader),
) -> dict:
    try:
        return PatchWriter(reader).draft(
            PatchDraftInput(
                target_file=request.target_file,
                intent=request.intent,
                new_content=request.new_content,
                operation=request.operation,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

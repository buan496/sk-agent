from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.config import Settings, get_settings
from app.services.repo_reader import RepoReader

router = APIRouter(prefix="/repo", tags=["repo"])


def get_repo_reader(settings: Settings = Depends(get_settings)) -> RepoReader:
    return RepoReader(settings)


@router.get("/files")
def list_repo_files(reader: RepoReader = Depends(get_repo_reader)) -> dict:
    return reader.list_files()


@router.get("/file")
def read_repo_file(
    path: str = Query(..., description="Repository-relative file path"),
    reader: RepoReader = Depends(get_repo_reader),
) -> dict:
    return reader.read_file(path)


@router.get("/canonical")
def read_canonical_files(reader: RepoReader = Depends(get_repo_reader)) -> dict:
    return reader.read_canonical_files()

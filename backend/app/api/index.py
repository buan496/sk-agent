from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.repo import get_repo_reader
from app.services.indexer import Indexer
from app.services.repo_reader import RepoReader

router = APIRouter(prefix="/index", tags=["index"])


def get_indexer(reader: RepoReader = Depends(get_repo_reader)) -> Indexer:
    return Indexer(reader)


@router.post("/rebuild")
def rebuild_index(indexer: Indexer = Depends(get_indexer)) -> dict:
    return indexer.rebuild()


@router.get("/status")
def index_status(indexer: Indexer = Depends(get_indexer)) -> dict:
    return indexer.status()


@router.get("/chunks")
def chunks_for_file(
    file_path: str = Query(..., description="Repository-relative markdown file path"),
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    return indexer.chunks_for_file(file_path)

from __future__ import annotations

from typing import Any

from app.config import CANONICAL_FILES
from app.services.repo_reader import RepoReader


UNREAD_MESSAGE = "本次未读取到，文件未读取到不等于文件不存在"


def canonical_preflight(reader: RepoReader) -> dict[str, Any]:
    canonical = reader.read_canonical_files()
    read_files = [_read_file_summary(item) for item in canonical.get("files", [])]
    return {
        "status": canonical.get("status"),
        "canonical_files": list(CANONICAL_FILES),
        "read_count": canonical.get("read_count", 0),
        "total": canonical.get("total", len(CANONICAL_FILES)),
        "read_files": read_files,
    }


def merge_read_files(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for group in groups:
        for item in group:
            path = str(item.get("path") or "")
            key = path or str(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _read_file_summary(result: dict[str, Any]) -> dict[str, Any]:
    file_meta = result.get("file") or {}
    status = result.get("status")
    message = result.get("message")
    if status and status != "ok" and not message:
        message = UNREAD_MESSAGE
    return {
        "path": result.get("path"),
        "status": status,
        "source": file_meta.get("source") or result.get("source"),
        "size": file_meta.get("size"),
        "last_modified": file_meta.get("last_modified"),
        "message": message,
    }

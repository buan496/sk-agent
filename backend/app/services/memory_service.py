from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from app.db import ensure_schema, get_connection


MEMORY_FILES = {
    "core_memory": "core_memory.md",
    "constitution": "constitution.md",
    "agent_registry": "agent_registry.md",
    "gpts_registry": "gpts_registry.md",
    "internal_roles": "internal_roles.md",
    "role_prompt_mapping": "role_prompt_mapping.yml",
    "external_tools": "external_tools.md",
    "drift_log": "episodes/drift-log.md",
    "agent_lessons": "episodes/agent-lessons.md",
    "role_lessons": "episodes/role-lessons.md",
    "routing_lessons": "episodes/routing-lessons.md",
}


def read_memory_file(name: str) -> str:
    relative_path = MEMORY_FILES[name]
    path = _memory_root() / relative_path
    return path.read_text(encoding="utf-8")


def create_external_agent_run(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO external_agent_runs (
                    agent_type, agent_name, task_type, input_summary, output_summary,
                    source_link_or_file, related_sk_files_json, status,
                    should_ingest, ingested, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at, agent_type, agent_name, task_type,
                          input_summary, output_summary, source_link_or_file,
                          related_sk_files_json, status, should_ingest, ingested, notes;
                """,
                (
                    payload["agent_type"],
                    payload["agent_name"],
                    payload["task_type"],
                    payload["input_summary"],
                    payload["output_summary"],
                    payload.get("source_link_or_file"),
                    Jsonb(payload.get("related_sk_files", [])),
                    payload["status"],
                    bool(payload.get("should_ingest", False)),
                    bool(payload.get("ingested", False)),
                    payload.get("notes"),
                ),
            )
            return _normalize_external_run(cursor.fetchone())


def list_external_agent_runs(limit: int = 20) -> list[dict[str, Any]]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, created_at, agent_type, agent_name, task_type,
                       input_summary, output_summary, source_link_or_file,
                       related_sk_files_json, status, should_ingest, ingested, notes
                FROM external_agent_runs
                ORDER BY created_at DESC, id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return [_normalize_external_run(row) for row in cursor.fetchall()]


def _normalize_external_run(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["related_sk_files"] = result.pop("related_sk_files_json") or []
    return result


def _memory_root() -> Path:
    configured = os.getenv("MEMORY_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "memory"

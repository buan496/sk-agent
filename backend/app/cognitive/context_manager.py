from __future__ import annotations

import uuid
from typing import Any

from psycopg.types.json import Jsonb

from app.db import ensure_schema, get_connection


def get_or_create_session(session_id: str | None, title: str, topic: str) -> dict[str, Any]:
    ensure_schema()
    resolved_id = (session_id or "").strip() or str(uuid.uuid4())
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO cognitive_sessions (id, title, current_topic, cognitive_state_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET updated_at = now()
                RETURNING id, created_at, updated_at, title, status, current_topic,
                          active_entity_slug, cognitive_state_json;
                """,
                (resolved_id, title[:120], topic[:120], Jsonb({})),
            )
            return _normalize_session(cursor.fetchone())


def load_session(session_id: str) -> dict[str, Any] | None:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, created_at, updated_at, title, status, current_topic,
                       active_entity_slug, cognitive_state_json
                FROM cognitive_sessions
                WHERE id = %s;
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            return _normalize_session(row) if row else None


def update_session_state(
    session_id: str,
    current_topic: str,
    active_entity_slug: str,
    cognitive_state: dict[str, Any],
) -> dict[str, Any]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE cognitive_sessions
                SET updated_at = now(),
                    current_topic = %s,
                    active_entity_slug = %s,
                    cognitive_state_json = %s
                WHERE id = %s
                RETURNING id, created_at, updated_at, title, status, current_topic,
                          active_entity_slug, cognitive_state_json;
                """,
                (current_topic[:120], active_entity_slug, Jsonb(cognitive_state), session_id),
            )
            return _normalize_session(cursor.fetchone())


def add_message(
    session_id: str,
    role: str,
    content: str,
    read_files: list[dict[str, Any]] | None = None,
    structured_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO cognitive_messages (
                    session_id, role, content, read_files_json, structured_output_json
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, session_id, created_at, role, content,
                          read_files_json, structured_output_json;
                """,
                (
                    session_id,
                    role,
                    content,
                    Jsonb(read_files or []),
                    Jsonb(structured_output or {}),
                ),
            )
            return _normalize_message(cursor.fetchone())


def recent_messages(session_id: str, limit: int = 12) -> list[dict[str, Any]]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, session_id, created_at, role, content,
                       read_files_json, structured_output_json
                FROM cognitive_messages
                WHERE session_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s;
                """,
                (session_id, limit),
            )
            return [_normalize_message(row) for row in reversed(cursor.fetchall())]


def list_sessions(limit: int = 20) -> list[dict[str, Any]]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, created_at, updated_at, title, status, current_topic,
                       active_entity_slug, cognitive_state_json
                FROM cognitive_sessions
                ORDER BY updated_at DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return [_normalize_session(row) for row in cursor.fetchall()]


def _normalize_session(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ["created_at", "updated_at"]:
        if result.get(key) is not None:
            result[key] = result[key].isoformat()
    result["cognitive_state"] = result.pop("cognitive_state_json") or {}
    return result


def _normalize_message(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    if result.get("created_at") is not None:
        result["created_at"] = result["created_at"].isoformat()
    result["read_files"] = result.pop("read_files_json") or []
    result["structured_output"] = result.pop("structured_output_json") or {}
    return result

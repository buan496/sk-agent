from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from app.cognitive.thought_tracker import ThoughtEntity
from app.db import ensure_schema, get_connection


def upsert_entities(session_id: str, entities: list[ThoughtEntity]) -> list[dict[str, Any]]:
    ensure_schema()
    results: list[dict[str, Any]] = []
    slugs = [entity.slug for entity in entities]
    with get_connection() as connection:
        with connection.cursor() as cursor:
            for entity in entities:
                related = [slug for slug in slugs if slug != entity.slug]
                cursor.execute(
                    """
                    INSERT INTO cognitive_entities (
                        session_id, name, slug, entity_type, mention_count, related_json
                    )
                    VALUES (%s, %s, %s, %s, 1, %s)
                    ON CONFLICT (session_id, slug) DO UPDATE
                    SET updated_at = now(),
                        mention_count = cognitive_entities.mention_count + 1,
                        entity_type = CASE
                            WHEN cognitive_entities.entity_type = 'unknown' THEN EXCLUDED.entity_type
                            ELSE cognitive_entities.entity_type
                        END,
                        related_json = COALESCE((
                            SELECT jsonb_agg(DISTINCT value)
                            FROM jsonb_array_elements_text(cognitive_entities.related_json || EXCLUDED.related_json) AS value
                        ), '[]'::jsonb)
                    RETURNING id, session_id, created_at, updated_at, name, slug,
                              entity_type, mention_count, related_json;
                    """,
                    (
                        session_id,
                        entity.name,
                        entity.slug,
                        entity.entity_type,
                        Jsonb(related),
                    ),
                )
                results.append(_normalize_entity(cursor.fetchone()))
    return results


def list_entities(session_id: str) -> list[dict[str, Any]]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, session_id, created_at, updated_at, name, slug,
                       entity_type, mention_count, related_json
                FROM cognitive_entities
                WHERE session_id = %s
                ORDER BY mention_count DESC, updated_at DESC;
                """,
                (session_id,),
            )
            return [_normalize_entity(row) for row in cursor.fetchall()]


def _normalize_entity(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ["created_at", "updated_at"]:
        if result.get(key) is not None:
            result[key] = result[key].isoformat()
    result["related"] = result.pop("related_json") or []
    return result

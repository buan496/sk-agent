from __future__ import annotations

import re
from typing import Any

from psycopg.types.json import Jsonb

from app.db import ensure_schema, get_connection
from app.roles.role_router import get_internal_role_run
from app.services.evidence_classifier import candidate_level_for_source, confidence_for_source
from app.services.source_reader import read_source


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return normalized or "research-object"


def create_or_get_research_object(name: str, slug: str | None = None, notes: str | None = None) -> dict[str, Any]:
    ensure_schema()
    object_slug = slugify(slug or name)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO research_objects (slug, name, research_target, notes)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET updated_at = now(),
                    name = EXCLUDED.name,
                    notes = COALESCE(EXCLUDED.notes, research_objects.notes)
                RETURNING id, created_at, updated_at, slug, name, status,
                          research_target, summary, notes;
                """,
                (object_slug, name.strip(), name.strip(), notes),
            )
            return _normalize_object(cursor.fetchone())


def list_research_objects(limit: int = 50) -> list[dict[str, Any]]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT o.id, o.created_at, o.updated_at, o.slug, o.name, o.status,
                       o.research_target, o.summary, o.notes,
                       COUNT(DISTINCT s.id) AS source_count,
                       COUNT(DISTINCT f.id) AS fact_count
                FROM research_objects o
                LEFT JOIN research_sources s ON s.object_id = o.id
                LEFT JOIN research_facts f ON f.object_id = o.id
                GROUP BY o.id
                ORDER BY o.updated_at DESC, o.id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return [_normalize_object(row) for row in cursor.fetchall()]


def get_research_state(slug: str) -> dict[str, Any] | None:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            obj = _get_object_by_slug(cursor, slug)
            if not obj:
                return None
            cursor.execute(
                """
                SELECT id, object_id, created_at, updated_at, url, title, source_type,
                       source_reason, evidence_level, read_status, clean_text,
                       metadata_json, extracted_facts_json, candidate_claims_json,
                       source_quotes_json, last_read_at
                FROM research_sources
                WHERE object_id = %s
                ORDER BY updated_at DESC, id DESC;
                """,
                (obj["id"],),
            )
            sources = [_normalize_source(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                SELECT id, object_id, source_id, created_at, updated_at, fact_text,
                       source_url, source_type, evidence_level, confidence, status, notes
                FROM research_facts
                WHERE object_id = %s
                ORDER BY updated_at DESC, id DESC;
                """,
                (obj["id"],),
            )
            facts = [_normalize_fact(row) for row in cursor.fetchall()]
    return {
        "object": obj,
        "sources": sources,
        "facts": facts,
        "counts": {
            "sources": len(sources),
            "read_sources": len([item for item in sources if item["read_status"] == "read"]),
            "facts": len(facts),
            "confirmed_facts": len([item for item in facts if item["status"] == "confirmed"]),
            "candidate_facts": len([item for item in facts if item["status"] == "candidate"]),
        },
        "gaps": _compute_gaps(sources, facts),
        "risks": _compute_risks(sources, facts),
        "next_actions": _compute_next_actions(sources, facts),
        "status_note": "Research state is accumulated candidate evidence. Canonical files remain the source of truth.",
    }


def add_candidate_source(slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            obj = _get_object_by_slug(cursor, slug)
            if not obj:
                raise ValueError("research_object_not_found")
            source = _upsert_source(cursor, obj["id"], payload)
            _touch_object(cursor, obj["id"])
            return source


def read_source_into_state(slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_schema()
    reading = read_source(
        url=str(payload["url"]),
        source_type=str(payload.get("source_type") or "unknown"),
        max_chars=int(payload.get("max_chars") or 12000),
    )
    source_payload = {
        "url": payload["url"],
        "title": payload.get("title") or reading.get("title") or "",
        "source_type": payload.get("source_type") or reading.get("source_type") or "unknown",
        "source_reason": payload.get("source_reason") or "",
        "evidence_level": payload.get("evidence_level"),
        "read_status": "read" if reading.get("status") == "ok" else "read_failed",
        "clean_text": reading.get("clean_text") or "",
        "metadata": reading.get("metadata") or {},
        "extracted_facts": reading.get("extracted_facts") or [],
        "candidate_claims": reading.get("candidate_claims") or [],
        "source_quotes": reading.get("source_quotes") or [],
        "mark_read": reading.get("status") == "ok",
    }
    with get_connection() as connection:
        with connection.cursor() as cursor:
            obj = _get_object_by_slug(cursor, slug)
            if not obj:
                raise ValueError("research_object_not_found")
            source = _upsert_source(cursor, obj["id"], source_payload)
            facts = _insert_facts_from_reading(cursor, obj["id"], source, reading)
            _touch_object(cursor, obj["id"])
            return {
                "source": source,
                "reading": reading,
                "facts_added": facts,
            }


def ingest_role_run(slug: str, run_id: int) -> dict[str, Any]:
    run = get_internal_role_run(run_id)
    if not run:
        raise ValueError("internal_role_run_not_found")
    structured = run.get("structured_output") or {}
    evidence_ledger = structured.get("evidence_ledger") or []
    source_readings = structured.get("source_readings") or []
    ensure_schema()
    sources_added: list[dict[str, Any]] = []
    facts_added: list[dict[str, Any]] = []
    with get_connection() as connection:
        with connection.cursor() as cursor:
            obj = _get_object_by_slug(cursor, slug)
            if not obj:
                raise ValueError("research_object_not_found")
            for item in evidence_ledger:
                if not isinstance(item, dict) or not item.get("source_url"):
                    continue
                source = _upsert_source(
                    cursor,
                    obj["id"],
                    {
                        "url": item.get("source_url"),
                        "title": item.get("source_title") or "",
                        "source_type": item.get("source_type") or "unknown",
                        "source_reason": item.get("source_reason") or "",
                        "evidence_level": item.get("evidence_level"),
                        "read_status": "candidate",
                    },
                )
                sources_added.append(source)
                fact = _insert_fact(
                    cursor,
                    obj["id"],
                    source["id"],
                    str(item.get("claim") or "Candidate source found."),
                    source["url"],
                    source["source_type"],
                    source["evidence_level"],
                    float(item.get("confidence") or confidence_for_source(source["source_type"])),
                    "candidate",
                    "Imported from internal_role_run evidence_ledger.",
                )
                facts_added.append(fact)
            for reading in source_readings:
                if not isinstance(reading, dict) or not reading.get("url"):
                    continue
                source = _upsert_source(
                    cursor,
                    obj["id"],
                    {
                        "url": reading.get("url"),
                        "title": reading.get("title") or "",
                        "source_type": reading.get("source_type") or "unknown",
                        "read_status": "read" if reading.get("status") == "ok" else "read_failed",
                        "clean_text": reading.get("clean_text") or "",
                        "metadata": reading.get("metadata") or {},
                        "extracted_facts": reading.get("extracted_facts") or [],
                        "candidate_claims": reading.get("candidate_claims") or [],
                        "source_quotes": reading.get("source_quotes") or [],
                        "mark_read": reading.get("status") == "ok",
                    },
                )
                sources_added.append(source)
                facts_added.extend(_insert_facts_from_reading(cursor, obj["id"], source, reading))
            _touch_object(cursor, obj["id"])
    return {
        "run_id": run_id,
        "sources_added": sources_added,
        "facts_added": facts_added,
        "source_count": len(sources_added),
        "fact_count": len(facts_added),
    }


def _upsert_source(cursor: Any, object_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    source_type = str(payload.get("source_type") or "unknown")
    evidence_level = payload.get("evidence_level") or candidate_level_for_source(source_type)
    cursor.execute(
        """
        INSERT INTO research_sources (
            object_id, url, title, source_type, source_reason, evidence_level,
            read_status, clean_text, metadata_json, extracted_facts_json,
            candidate_claims_json, source_quotes_json, last_read_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                CASE WHEN %s THEN now() ELSE NULL END)
        ON CONFLICT (object_id, url) DO UPDATE
        SET updated_at = now(),
            title = COALESCE(NULLIF(EXCLUDED.title, ''), research_sources.title),
            source_type = EXCLUDED.source_type,
            source_reason = COALESCE(NULLIF(EXCLUDED.source_reason, ''), research_sources.source_reason),
            evidence_level = EXCLUDED.evidence_level,
            read_status = EXCLUDED.read_status,
            clean_text = COALESCE(NULLIF(EXCLUDED.clean_text, ''), research_sources.clean_text),
            metadata_json = CASE
                WHEN EXCLUDED.metadata_json = '{}'::jsonb THEN research_sources.metadata_json
                ELSE EXCLUDED.metadata_json
            END,
            extracted_facts_json = CASE
                WHEN EXCLUDED.extracted_facts_json = '[]'::jsonb THEN research_sources.extracted_facts_json
                ELSE EXCLUDED.extracted_facts_json
            END,
            candidate_claims_json = CASE
                WHEN EXCLUDED.candidate_claims_json = '[]'::jsonb THEN research_sources.candidate_claims_json
                ELSE EXCLUDED.candidate_claims_json
            END,
            source_quotes_json = CASE
                WHEN EXCLUDED.source_quotes_json = '[]'::jsonb THEN research_sources.source_quotes_json
                ELSE EXCLUDED.source_quotes_json
            END,
            last_read_at = COALESCE(EXCLUDED.last_read_at, research_sources.last_read_at)
        RETURNING id, object_id, created_at, updated_at, url, title, source_type,
                  source_reason, evidence_level, read_status, clean_text,
                  metadata_json, extracted_facts_json, candidate_claims_json,
                  source_quotes_json, last_read_at;
        """,
        (
            object_id,
            payload["url"],
            payload.get("title") or "",
            source_type,
            payload.get("source_reason") or "",
            evidence_level,
            payload.get("read_status") or "candidate",
            payload.get("clean_text") or "",
            Jsonb(payload.get("metadata") or {}),
            Jsonb(payload.get("extracted_facts") or []),
            Jsonb(payload.get("candidate_claims") or []),
            Jsonb(payload.get("source_quotes") or []),
            bool(payload.get("mark_read")),
        ),
    )
    return _normalize_source(cursor.fetchone())


def _insert_facts_from_reading(
    cursor: Any, object_id: int, source: dict[str, Any], reading: dict[str, Any]
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for fact_text in reading.get("extracted_facts") or []:
        facts.append(
            _insert_fact(
                cursor,
                object_id,
                source["id"],
                str(fact_text),
                source["url"],
                source["source_type"],
                source["evidence_level"],
                confidence_for_source(source["source_type"]),
                "candidate",
                "Extracted from source_reader clean text.",
            )
        )
    for claim in reading.get("candidate_claims") or []:
        if not isinstance(claim, dict) or not claim.get("claim"):
            continue
        facts.append(
            _insert_fact(
                cursor,
                object_id,
                source["id"],
                str(claim.get("claim")),
                source["url"],
                source["source_type"],
                source["evidence_level"],
                float(claim.get("confidence") or confidence_for_source(source["source_type"])),
                "candidate",
                "Imported from source_reader candidate_claims.",
            )
        )
    return facts


def _insert_fact(
    cursor: Any,
    object_id: int,
    source_id: int | None,
    fact_text: str,
    source_url: str,
    source_type: str,
    evidence_level: str,
    confidence: float,
    status: str,
    notes: str,
) -> dict[str, Any]:
    cursor.execute(
        """
        INSERT INTO research_facts (
            object_id, source_id, fact_text, source_url, source_type,
            evidence_level, confidence, status, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, object_id, source_id, created_at, updated_at, fact_text,
                  source_url, source_type, evidence_level, confidence, status, notes;
        """,
        (
            object_id,
            source_id,
            fact_text,
            source_url,
            source_type,
            evidence_level,
            confidence,
            status,
            notes,
        ),
    )
    return _normalize_fact(cursor.fetchone())


def _get_object_by_slug(cursor: Any, slug: str) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT id, created_at, updated_at, slug, name, status,
               research_target, summary, notes
        FROM research_objects
        WHERE slug = %s;
        """,
        (slugify(slug),),
    )
    row = cursor.fetchone()
    return _normalize_object(row) if row else None


def _touch_object(cursor: Any, object_id: int) -> None:
    cursor.execute("UPDATE research_objects SET updated_at = now() WHERE id = %s;", (object_id,))


def _compute_gaps(sources: list[dict[str, Any]], facts: list[dict[str, Any]]) -> list[str]:
    source_types = {source["source_type"] for source in sources}
    gaps: list[str] = []
    if "official" not in source_types:
        gaps.append("Missing official/product page source.")
    if "app_store" not in source_types:
        gaps.append("Missing app store or user feedback source.")
    if "company_profile" not in source_types:
        gaps.append("Missing company profile source.")
    if not any(source["read_status"] == "read" for source in sources):
        gaps.append("Candidate sources have not been read into clean text yet.")
    if not any(fact["status"] == "confirmed" for fact in facts):
        gaps.append("No confirmed facts yet; all facts are still candidates.")
    return gaps


def _compute_risks(sources: list[dict[str, Any]], facts: list[dict[str, Any]]) -> list[str]:
    risks: list[str] = ["Research state cannot override SK canonical files."]
    if any(source["source_type"] in {"community", "unknown"} for source in sources):
        risks.append("Some sources are community or unknown sources and need careful review.")
    if facts and not any(fact["evidence_level"].startswith("A_") for fact in facts):
        risks.append("Current facts lack A-level candidate support.")
    return risks


def _compute_next_actions(sources: list[dict[str, Any]], facts: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    unread = [source for source in sources if source["read_status"] == "candidate"]
    if unread:
        actions.append("Read the highest quality candidate source into clean text.")
    if facts and not any(fact["status"] == "confirmed" for fact in facts):
        actions.append("Human review candidate facts and mark which ones are reliable.")
    if not sources:
        actions.append("Run deep research with web search, then ingest candidate sources.")
    return actions or ["Use accumulated research state to draft the next judgment step."]


def _normalize_object(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ["created_at", "updated_at"]:
        if result.get(key) is not None:
            result[key] = result[key].isoformat()
    return result


def _normalize_source(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ["created_at", "updated_at", "last_read_at"]:
        if result.get(key) is not None:
            result[key] = result[key].isoformat()
    result["metadata"] = result.pop("metadata_json") or {}
    result["extracted_facts"] = result.pop("extracted_facts_json") or []
    result["candidate_claims"] = result.pop("candidate_claims_json") or []
    result["source_quotes"] = result.pop("source_quotes_json") or []
    return result


def _normalize_fact(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ["created_at", "updated_at"]:
        if result.get(key) is not None:
            result[key] = result[key].isoformat()
    return result

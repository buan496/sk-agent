from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings


def get_database_url() -> str:
    return get_settings().database_url


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    connection = psycopg.connect(get_database_url(), row_factory=dict_row)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def ensure_schema() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id BIGSERIAL PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    size BIGINT NOT NULL DEFAULT 0,
                    last_modified TIMESTAMPTZ NULL,
                    source TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    indexed_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id BIGSERIAL PRIMARY KEY,
                    file_id BIGINT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                    file_path TEXT NOT NULL,
                    heading TEXT NULL,
                    content TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    chunk_type TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    content_sha256 TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS index_runs (
                    id BIGSERIAL PRIMARY KEY,
                    status TEXT NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    finished_at TIMESTAMPTZ NULL,
                    source TEXT NULL,
                    total_files INTEGER NOT NULL DEFAULT 0,
                    indexed_files INTEGER NOT NULL DEFAULT 0,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS external_agent_runs (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    agent_type TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    input_summary TEXT NOT NULL,
                    output_summary TEXT NOT NULL,
                    source_link_or_file TEXT NULL,
                    related_sk_files_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    status TEXT NOT NULL,
                    should_ingest BOOLEAN NOT NULL DEFAULT false,
                    ingested BOOLEAN NOT NULL DEFAULT false,
                    notes TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS internal_role_runs (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    role_id TEXT NOT NULL,
                    role_name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    input_summary TEXT NOT NULL,
                    read_files_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    structured_output_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    conclusion TEXT NOT NULL,
                    risks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    minimal_next_step TEXT NOT NULL,
                    answer_markdown TEXT NOT NULL,
                    should_ingest BOOLEAN NOT NULL DEFAULT false,
                    ingested BOOLEAN NOT NULL DEFAULT false,
                    notes TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS research_objects (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    slug TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    research_target TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    notes TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS research_sources (
                    id BIGSERIAL PRIMARY KEY,
                    object_id BIGINT NOT NULL REFERENCES research_objects(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    url TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    source_type TEXT NOT NULL DEFAULT 'unknown',
                    source_reason TEXT NOT NULL DEFAULT '',
                    evidence_level TEXT NOT NULL DEFAULT 'X_candidate',
                    read_status TEXT NOT NULL DEFAULT 'candidate',
                    clean_text TEXT NOT NULL DEFAULT '',
                    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    extracted_facts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    candidate_claims_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    source_quotes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    last_read_at TIMESTAMPTZ NULL,
                    UNIQUE(object_id, url)
                );

                CREATE TABLE IF NOT EXISTS research_facts (
                    id BIGSERIAL PRIMARY KEY,
                    object_id BIGINT NOT NULL REFERENCES research_objects(id) ON DELETE CASCADE,
                    source_id BIGINT NULL REFERENCES research_sources(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    fact_text TEXT NOT NULL,
                    source_url TEXT NOT NULL DEFAULT '',
                    source_type TEXT NOT NULL DEFAULT 'unknown',
                    evidence_level TEXT NOT NULL DEFAULT 'X_candidate',
                    confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'candidate',
                    notes TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS cognitive_sessions (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    title TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    current_topic TEXT NOT NULL DEFAULT '',
                    active_entity_slug TEXT NOT NULL DEFAULT '',
                    cognitive_state_json JSONB NOT NULL DEFAULT '{}'::jsonb
                );

                CREATE TABLE IF NOT EXISTS cognitive_entities (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES cognitive_sessions(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    entity_type TEXT NOT NULL DEFAULT 'unknown',
                    mention_count INTEGER NOT NULL DEFAULT 1,
                    related_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    UNIQUE(session_id, slug)
                );

                CREATE TABLE IF NOT EXISTS cognitive_messages (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES cognitive_sessions(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    read_files_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    structured_output_json JSONB NOT NULL DEFAULT '{}'::jsonb
                );

                CREATE TABLE IF NOT EXISTS cognitive_judgments (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES cognitive_sessions(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    entity_slug TEXT NOT NULL DEFAULT '',
                    step INTEGER NOT NULL,
                    judgment TEXT NOT NULL,
                    why TEXT NOT NULL DEFAULT '',
                    evidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    risks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    unresolved_json JSONB NOT NULL DEFAULT '[]'::jsonb
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks(file_path);
                CREATE INDEX IF NOT EXISTS idx_chunks_heading ON chunks(heading);
                CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
                CREATE INDEX IF NOT EXISTS idx_external_agent_runs_created_at
                    ON external_agent_runs(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_internal_role_runs_created_at
                    ON internal_role_runs(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_research_objects_slug
                    ON research_objects(slug);
                CREATE INDEX IF NOT EXISTS idx_research_sources_object_id
                    ON research_sources(object_id);
                CREATE INDEX IF NOT EXISTS idx_research_facts_object_id
                    ON research_facts(object_id);
                CREATE INDEX IF NOT EXISTS idx_cognitive_sessions_updated_at
                    ON cognitive_sessions(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_cognitive_entities_session_id
                    ON cognitive_entities(session_id);
                CREATE INDEX IF NOT EXISTS idx_cognitive_messages_session_id
                    ON cognitive_messages(session_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_cognitive_judgments_session_id
                    ON cognitive_judgments(session_id, step DESC);
                """
            )

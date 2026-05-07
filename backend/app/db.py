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

                CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks(file_path);
                CREATE INDEX IF NOT EXISTS idx_chunks_heading ON chunks(heading);
                CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
                """
            )

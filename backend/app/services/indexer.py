from __future__ import annotations

import hashlib
from typing import Any

from app.db import ensure_schema, get_connection
from app.services.markdown_parser import MarkdownChunk, parse_markdown
from app.services.repo_reader import RepoReader


class Indexer:
    def __init__(self, reader: RepoReader) -> None:
        self.reader = reader

    def rebuild(self) -> dict[str, Any]:
        ensure_schema()
        run_id = self._start_run()

        try:
            file_tree = self.reader.list_files()
            if file_tree.get("status") != "ok":
                message = file_tree.get("message") or "仓库文件树本次未读取到"
                self._finish_run(run_id, "failed", error_message=message)
                return {"status": "failed", "run_id": run_id, "message": message}

            markdown_files = [
                item
                for item in file_tree.get("files", [])
                if str(item.get("path", "")).lower().endswith(".md")
                and _is_sk_content_path(str(item.get("path", "")))
            ]

            indexed_files = 0
            chunk_count = 0
            failures: list[dict[str, str]] = []

            self._clear_index()
            for item in markdown_files:
                path = str(item.get("path", ""))
                file_result = self.reader.read_file(path)
                if file_result.get("status") != "ok":
                    failures.append(
                        {
                            "path": path,
                            "status": str(file_result.get("status")),
                            "message": str(file_result.get("message", "")),
                        }
                    )
                    continue

                content = str(file_result.get("content") or "")
                chunks = parse_markdown(path, content)
                file_id = self._upsert_file(
                    path=path,
                    size=int((file_result.get("file") or {}).get("size") or len(content.encode("utf-8"))),
                    last_modified=(file_result.get("file") or {}).get("last_modified"),
                    source=str((file_result.get("file") or {}).get("source") or file_result.get("source") or "unknown"),
                    content=content,
                )
                self._replace_chunks(file_id, path, chunks)
                indexed_files += 1
                chunk_count += len(chunks)

            status = "ok" if not failures else "partial"
            self._finish_run(
                run_id,
                status,
                total_files=len(markdown_files),
                indexed_files=indexed_files,
                chunk_count=chunk_count,
                error_message=f"{len(failures)} files failed" if failures else None,
            )
            return {
                "status": status,
                "run_id": run_id,
                "total_files": len(markdown_files),
                "indexed_files": indexed_files,
                "chunk_count": chunk_count,
                "failures": failures[:20],
            }
        except Exception as exc:
            self._finish_run(run_id, "failed", error_message=str(exc))
            raise

    def status(self) -> dict[str, Any]:
        ensure_schema()
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) AS count FROM files;")
                file_count = cursor.fetchone()["count"]
                cursor.execute("SELECT count(*) AS count FROM chunks;")
                chunk_count = cursor.fetchone()["count"]
                cursor.execute(
                    """
                    SELECT id, status, started_at, finished_at, source, total_files,
                           indexed_files, chunk_count, error_message
                    FROM index_runs
                    ORDER BY id DESC
                    LIMIT 1;
                    """
                )
                latest_run = cursor.fetchone()
        return {
            "status": "ok",
            "file_count": file_count,
            "chunk_count": chunk_count,
            "latest_run": latest_run,
        }

    def chunks_for_file(self, file_path: str) -> dict[str, Any]:
        ensure_schema()
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT file_path, heading, content, start_line, end_line,
                           chunk_type, ordinal
                    FROM chunks
                    WHERE file_path = %s
                    ORDER BY ordinal ASC;
                    """,
                    (file_path,),
                )
                chunks = cursor.fetchall()
        return {
            "status": "ok",
            "file_path": file_path,
            "count": len(chunks),
            "chunks": chunks,
        }

    def _start_run(self) -> int:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO index_runs (status, source) VALUES ('running', %s) RETURNING id;",
                    (self._source_name(),),
                )
                return int(cursor.fetchone()["id"])

    def _finish_run(
        self,
        run_id: int,
        status: str,
        total_files: int = 0,
        indexed_files: int = 0,
        chunk_count: int = 0,
        error_message: str | None = None,
    ) -> None:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE index_runs
                    SET status = %s,
                        finished_at = now(),
                        total_files = %s,
                        indexed_files = %s,
                        chunk_count = %s,
                        error_message = %s
                    WHERE id = %s;
                    """,
                    (status, total_files, indexed_files, chunk_count, error_message, run_id),
                )

    def _clear_index(self) -> None:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE chunks, files RESTART IDENTITY CASCADE;")

    def _upsert_file(
        self,
        path: str,
        size: int,
        last_modified: str | None,
        source: str,
        content: str,
    ) -> int:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO files (path, size, last_modified, source, content_sha256)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (path) DO UPDATE
                    SET size = EXCLUDED.size,
                        last_modified = EXCLUDED.last_modified,
                        source = EXCLUDED.source,
                        content_sha256 = EXCLUDED.content_sha256,
                        indexed_at = now()
                    RETURNING id;
                    """,
                    (path, size, last_modified, source, _sha256(content)),
                )
                return int(cursor.fetchone()["id"])

    def _replace_chunks(self, file_id: int, file_path: str, chunks: list[MarkdownChunk]) -> None:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM chunks WHERE file_id = %s;", (file_id,))
                for chunk in chunks:
                    cursor.execute(
                        """
                        INSERT INTO chunks (
                            file_id, file_path, heading, content, start_line, end_line,
                            chunk_type, ordinal, content_sha256
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            file_id,
                            file_path,
                            chunk.heading,
                            chunk.content,
                            chunk.start_line,
                            chunk.end_line,
                            chunk.chunk_type,
                            chunk.ordinal,
                            _sha256(chunk.content),
                        ),
                    )

    def _source_name(self) -> str:
        settings = self.reader.settings
        if settings.local_repo_path:
            return "local"
        if settings.github_repo:
            return "github"
        if settings.github_raw_base_url:
            return "github_raw"
        return "unknown"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


SKGPT_PATH_PREFIXES = (
    "skgpt/",
    ".skgpt/",
    "gpts/",
    "project-instructions/",
    "project_instructions/",
    "uploads/",
    "upload-lists/",
)


def _is_sk_content_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower().lstrip("/")
    return not any(normalized.startswith(prefix) for prefix in SKGPT_PATH_PREFIXES)

from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from app.config import Settings
from app.db import ensure_schema, get_connection
from app.roles.base_role import RoleContext
from app.roles.role_registry import role_registry
from app.services.canonical_preflight import canonical_preflight
from app.services.repo_reader import RepoReader
from app.services.web_search import search_web


TASK_ROLE_MAP = {
    "deep_research": "deep_researcher_role",
    "writing_workshop": "writing_workshop_role",
    "first_reader": "first_reader_role",
    "product_teardown": "product_teardown_role",
    "repo_governance": "repo_governance_role",
    "patch_draft": "patch_writer_role",
    "status_audit": "repo_governance_role",
    "article_publish_check": "article_publish_check_role",
}

WEB_ENABLED_ROLE_IDS = {
    "deep_researcher_role",
    "product_teardown_role",
    "article_publish_check_role",
}


class RoleRouter:
    def __init__(self, settings: Settings, reader: RepoReader) -> None:
        self.settings = settings
        self.reader = reader
        self.roles = role_registry()

    def run(
        self,
        task_type: str,
        user_input: str,
        notes: str = "",
        preferred_role: str | None = None,
        allow_web: bool = False,
        web_queries: list[str] | None = None,
    ) -> dict[str, Any]:
        role_id = preferred_role or TASK_ROLE_MAP.get(task_type)
        if not role_id or role_id not in self.roles:
            raise ValueError(f"Unsupported task_type or role: {task_type}")
        preflight = canonical_preflight(self.reader)
        selected_queries: list[str] = []
        web_results: list[dict[str, Any]] = []
        web_warnings: list[str] = []
        if allow_web and role_id not in WEB_ENABLED_ROLE_IDS:
            web_warnings.append(f"{role_id} 不允许联网；已忽略 allow_web=true。")
        elif allow_web:
            selected_queries = _select_web_queries(web_queries, user_input)
            for query in selected_queries:
                try:
                    response = search_web(query=query, limit=5, settings=self.settings)
                    for item in response.get("results", []):
                        enriched = dict(item)
                        enriched["query"] = query
                        web_results.append(enriched)
                except Exception as exc:
                    web_warnings.append(f"搜索失败：{query}；{exc}")
        context = RoleContext(
            reader=self.reader,
            preflight=preflight,
            task_type=task_type,
            allow_web=allow_web,
            web_queries=selected_queries,
            web_results=web_results,
            web_warnings=web_warnings,
        )
        role = self.roles[role_id]
        result = role.run(user_input, notes, context)
        result["task_type"] = task_type
        result["status"] = "ok"
        if web_warnings and not result.get("warnings"):
            result["warnings"] = web_warnings
        run_record = create_internal_role_run(
            {
                "role_id": result["role_id"],
                "role_name": result["role_name"],
                "task_type": task_type,
                "input_summary": _summary(user_input),
                "read_files": result.get("read_files", []),
                "structured_output": result.get("structured_output", {}),
                "conclusion": result.get("conclusion", ""),
                "risks": result.get("risks", []),
                "minimal_next_step": result.get("minimal_next_step", ""),
                "answer_markdown": result.get("answer_markdown", ""),
                "should_ingest": bool(result.get("should_ingest", False)),
                "ingested": bool(result.get("ingested", False)),
                "notes": notes,
            }
        )
        result["run_id"] = run_record["id"]
        return result


def create_internal_role_run(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO internal_role_runs (
                    role_id, role_name, task_type, input_summary, read_files_json,
                    structured_output_json, conclusion, risks_json, minimal_next_step,
                    answer_markdown, should_ingest, ingested, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at, role_id, role_name, task_type, input_summary,
                          read_files_json, structured_output_json, conclusion, risks_json,
                          minimal_next_step, answer_markdown, should_ingest, ingested, notes;
                """,
                (
                    payload["role_id"],
                    payload["role_name"],
                    payload["task_type"],
                    payload["input_summary"],
                    Jsonb(payload.get("read_files", [])),
                    Jsonb(payload.get("structured_output", {})),
                    payload["conclusion"],
                    Jsonb(payload.get("risks", [])),
                    payload["minimal_next_step"],
                    payload["answer_markdown"],
                    bool(payload.get("should_ingest", False)),
                    bool(payload.get("ingested", False)),
                    payload.get("notes"),
                ),
            )
            return _normalize_role_run(cursor.fetchone())


def list_internal_role_runs(limit: int = 10) -> list[dict[str, Any]]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, created_at, role_id, role_name, task_type, input_summary,
                       read_files_json, structured_output_json, conclusion, risks_json,
                       minimal_next_step, answer_markdown, should_ingest, ingested, notes
                FROM internal_role_runs
                ORDER BY created_at DESC, id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return [_normalize_role_run(row) for row in cursor.fetchall()]


def _normalize_role_run(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["read_files"] = result.pop("read_files_json") or []
    result["structured_output"] = result.pop("structured_output_json") or {}
    result["risks"] = result.pop("risks_json") or []
    return result


def _summary(value: str) -> str:
    compact = " ".join((value or "").split())
    return compact[:500]


def _select_web_queries(web_queries: list[str] | None, user_input: str) -> list[str]:
    queries = [item.strip() for item in (web_queries or []) if item and item.strip()]
    if not queries:
        queries = [_summary(user_input)]
    return queries[:5]

from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from app.config import Settings
from app.db import ensure_schema, get_connection
from app.roles.base_role import RoleContext
from app.roles.role_registry import role_registry
from app.services.canonical_preflight import canonical_preflight
from app.services.conversation_intent import is_carryover_intent
from app.services.query_expander import expand_search_queries
from app.services.repo_reader import RepoReader
from app.services.source_reader import read_source
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
        conversation_id: str | None = None,
        read_sources: bool = False,
    ) -> dict[str, Any]:
        role_id = preferred_role or TASK_ROLE_MAP.get(task_type)
        if not role_id or role_id not in self.roles:
            raise ValueError(f"Unsupported task_type or role: {task_type}")
        preflight = canonical_preflight(self.reader)
        selected_queries: list[str] = []
        web_results: list[dict[str, Any]] = []
        source_readings: list[dict[str, Any]] = []
        web_warnings: list[str] = []
        carryover_intent = is_carryover_intent(user_input)
        carryover_context = _load_carryover_context(conversation_id)
        context_used = bool(carryover_intent and carryover_context)
        inherited_sources_count = _count_inherited_sources(carryover_context)
        if carryover_intent and not carryover_context:
            web_warnings.append("当前请求引用了上一轮结果，但系统没有找到可继承上下文。请在同一对话中继续，或粘贴上一轮候选来源。")
        elif allow_web and role_id not in WEB_ENABLED_ROLE_IDS:
            web_warnings.append(f"{role_id} 不允许联网；已忽略 allow_web=true。")
        elif allow_web and not carryover_intent:
            selected_queries = expand_search_queries(
                role_id=role_id,
                task_type=task_type,
                user_input=user_input,
                explicit_queries=web_queries,
                limit=5,
            )
            for query in selected_queries:
                try:
                    response = search_web(query=query, limit=5, settings=self.settings)
                    for item in response.get("results", []):
                        enriched = dict(item)
                        enriched["query"] = query
                        web_results.append(enriched)
                except Exception as exc:
                    web_warnings.append(f"搜索失败：{query}；{exc}")
            if read_sources and role_id == "deep_researcher_role":
                source_readings = _read_top_sources(web_results, web_warnings)
        context = RoleContext(
            reader=self.reader,
            preflight=preflight,
            task_type=task_type,
            allow_web=allow_web,
            web_queries=selected_queries,
            expanded_queries=selected_queries,
            web_results=web_results,
            web_warnings=web_warnings,
            read_sources=read_sources,
            source_readings=source_readings,
            carryover_intent=carryover_intent,
            carryover_context=carryover_context,
            context_used=context_used,
            inherited_sources_count=inherited_sources_count if context_used else 0,
            new_web_search_performed=bool(web_results),
        )
        role = self.roles[role_id]
        result = role.run(user_input, notes, context)
        result["task_type"] = task_type
        result["status"] = "ok"
        if web_warnings and not result.get("warnings"):
            result["warnings"] = web_warnings
        result["expanded_queries"] = selected_queries
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


def get_internal_role_run(run_id: int) -> dict[str, Any] | None:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, created_at, role_id, role_name, task_type, input_summary,
                       read_files_json, structured_output_json, conclusion, risks_json,
                       minimal_next_step, answer_markdown, should_ingest, ingested, notes
                FROM internal_role_runs
                WHERE id = %s;
                """,
                (run_id,),
            )
            row = cursor.fetchone()
            return _normalize_role_run(row) if row else None


def _normalize_role_run(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["read_files"] = result.pop("read_files_json") or []
    result["structured_output"] = result.pop("structured_output_json") or {}
    result["risks"] = result.pop("risks_json") or []
    return result


def _summary(value: str) -> str:
    compact = " ".join((value or "").split())
    return compact[:500]


def _load_carryover_context(conversation_id: str | None) -> dict[str, Any] | None:
    if not conversation_id:
        return None
    try:
        run_id = int(str(conversation_id).strip())
    except ValueError:
        return None
    return get_internal_role_run(run_id)


def _count_inherited_sources(context: dict[str, Any] | None) -> int:
    if not context:
        return 0
    structured = context.get("structured_output") or {}
    evidence = structured.get("evidence_ledger") or []
    return len(evidence) if isinstance(evidence, list) else 0


def _read_top_sources(web_results: list[dict[str, Any]], warnings: list[str]) -> list[dict[str, Any]]:
    readings: list[dict[str, Any]] = []
    for source_type in ["official", "app_store", "company_profile"]:
        item = next((result for result in web_results if result.get("source_type") == source_type), None)
        if not item:
            continue
        try:
            readings.append(
                read_source(
                    url=str(item.get("url") or ""),
                    source_type=source_type,
                    max_chars=12000,
                )
            )
        except Exception as exc:
            warnings.append(f"来源正文读取失败：{item.get('url')}；{exc}")
    return readings

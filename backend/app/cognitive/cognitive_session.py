from __future__ import annotations

from typing import Any

from app.cognitive.context_manager import (
    add_message,
    get_or_create_session,
    list_sessions,
    load_session,
    recent_messages,
    update_session_state,
)
from app.cognitive.entity_memory import list_entities, upsert_entities
from app.cognitive.judgment_state import add_judgment, build_judgment_update, list_judgments
from app.cognitive.thought_tracker import extract_entities, infer_topic
from app.config import Settings
from app.roles.role_router import RoleRouter
from app.services.canonical_preflight import canonical_preflight
from app.services.repo_reader import RepoReader
from app.services.research_state import create_or_get_research_object, get_research_state, ingest_role_run


def think(
    *,
    settings: Settings,
    reader: RepoReader,
    user_input: str,
    session_id: str | None = None,
    allow_web: bool = False,
    read_sources: bool = False,
) -> dict[str, Any]:
    initial_entities = extract_entities(user_input)
    initial_topic = infer_topic(user_input, entities=initial_entities)
    session = get_or_create_session(session_id, title=initial_topic, topic=initial_topic)
    previous_state = session.get("cognitive_state") or {}
    entities = initial_entities or extract_entities(previous_state.get("current_topic", ""))
    topic = infer_topic(user_input, session.get("current_topic") or "", entities)
    entity_records = upsert_entities(session["id"], entities) if entities else []
    active_entity_slug = entity_records[0]["slug"] if entity_records else session.get("active_entity_slug") or ""
    research_object = None
    research_state = None
    if active_entity_slug:
        research_object = create_or_get_research_object(
            name=entity_records[0]["name"] if entity_records else topic,
            slug=active_entity_slug,
            notes="Auto-created by Cognitive Flow OS.",
        )
        research_state = get_research_state(active_entity_slug)

    preflight = canonical_preflight(reader)
    operator_output = _maybe_run_operator(
        settings=settings,
        reader=reader,
        topic=topic,
        user_input=user_input,
        allow_web=allow_web,
        read_sources=read_sources,
    )
    if research_object and operator_output and operator_output.get("run_id"):
        try:
            ingest_role_run(active_entity_slug, int(operator_output["run_id"]))
            research_state = get_research_state(active_entity_slug)
        except Exception as exc:
            operator_output.setdefault("warnings", []).append(f"Research state 自动沉淀失败：{exc}")

    update = build_judgment_update(user_input, topic, previous_state, operator_output)
    cognitive_state = {
        "current_topic": topic,
        "active_entity_slug": active_entity_slug,
        "current_judgment": update["current_judgment"],
        "why": update["why"],
        "evidence": update["evidence"],
        "risks": update["risks"],
        "unresolved_questions": update["unresolved_questions"],
        "next_question": update["next_question"],
        "operator_used": operator_output.get("role_id") if operator_output else None,
        "research_object_slug": research_object.get("slug") if research_object else "",
    }
    session = update_session_state(session["id"], topic, active_entity_slug, cognitive_state)
    judgment = add_judgment(
        session_id=session["id"],
        entity_slug=active_entity_slug,
        judgment=update["current_judgment"],
        why=update["why"],
        evidence=update["evidence"],
        risks=update["risks"],
        unresolved=update["unresolved_questions"],
    )
    add_message(session["id"], "user", user_input, preflight.get("read_files", []), {"entities": entity_records})
    assistant_markdown = _human_markdown(
        topic=topic,
        update=update,
        operator_output=operator_output,
        research_state=research_state,
    )
    add_message(
        session["id"],
        "assistant",
        assistant_markdown,
        preflight.get("read_files", []),
        {
            "cognitive_state": cognitive_state,
            "operator_output": operator_output or {},
            "research_state_counts": (research_state or {}).get("counts", {}),
        },
    )
    return {
        "status": "ok",
        "session": session,
        "read_files": preflight.get("read_files", []),
        "current_topic": topic,
        "entities": list_entities(session["id"]),
        "current_judgment": update["current_judgment"],
        "why": update["why"],
        "evidence": update["evidence"],
        "risks": update["risks"],
        "unresolved_questions": update["unresolved_questions"],
        "next_question": update["next_question"],
        "operator_used": operator_output.get("role_id") if operator_output else None,
        "operator_output": operator_output,
        "research_object": research_object,
        "research_state": research_state,
        "judgment": judgment,
        "judgment_evolution": list_judgments(session["id"], limit=20),
        "messages": recent_messages(session["id"], limit=12),
        "answer_markdown": assistant_markdown,
        "structured_output": {
            "cognitive_state": cognitive_state,
            "operator_output": operator_output or {},
            "research_state": research_state or {},
        },
    }


def state(session_id: str) -> dict[str, Any] | None:
    session = load_session(session_id)
    if not session:
        return None
    active_slug = session.get("active_entity_slug") or ""
    return {
        "session": session,
        "entities": list_entities(session_id),
        "judgment_evolution": list_judgments(session_id, limit=50),
        "messages": recent_messages(session_id, limit=20),
        "research_state": get_research_state(active_slug) if active_slug else None,
    }


def sessions(limit: int = 20) -> list[dict[str, Any]]:
    return list_sessions(limit=limit)


def _maybe_run_operator(
    *,
    settings: Settings,
    reader: RepoReader,
    topic: str,
    user_input: str,
    allow_web: bool,
    read_sources: bool,
) -> dict[str, Any] | None:
    if not allow_web:
        return None
    task_input = f"{topic}\n\n用户当前思考：{user_input}"
    return RoleRouter(settings=settings, reader=reader).run(
        task_type="deep_research",
        user_input=task_input,
        allow_web=True,
        read_sources=read_sources,
    )


def _human_markdown(
    *,
    topic: str,
    update: dict[str, Any],
    operator_output: dict[str, Any] | None,
    research_state: dict[str, Any] | None,
) -> str:
    evidence = update.get("evidence") or []
    risks = update.get("risks") or []
    unresolved = update.get("unresolved_questions") or []
    counts = (research_state or {}).get("counts") or {}
    lines = [
        f"## 当前判断",
        update["current_judgment"],
        "",
        "## 为什么",
        update["why"],
        "",
        "## 当前证据",
    ]
    if evidence:
        for item in evidence[:6]:
            if isinstance(item, dict):
                source = item.get("source_title") or item.get("source_url") or "候选来源"
                level = item.get("evidence_level") or "candidate"
                lines.append(f"- {source}（{level}）")
            else:
                lines.append(f"- {item}")
    else:
        lines.append("- 暂无新增外部证据；本轮主要是延续和组织判断。")
    lines.extend(["", "## 当前风险"])
    lines.extend([f"- {item}" for item in risks] or ["- 暂无新增风险，但仍需 canonical files 校准。"])
    lines.extend(["", "## 未解决问题"])
    lines.extend([f"- {item}" for item in unresolved] or ["- 还需要补一个能改变判断的关键证据。"])
    lines.extend(["", "## 下一步最值得追的问题", update["next_question"]])
    if counts:
        lines.extend(
            [
                "",
                "## 研究状态",
                f"- 候选来源：{counts.get('sources', 0)}",
                f"- 已读来源：{counts.get('read_sources', 0)}",
                f"- 候选事实：{counts.get('facts', 0)}",
            ]
        )
    if operator_output:
        lines.extend(["", "## 本轮内部 operator", operator_output.get("role_name") or operator_output.get("role_id") or "-"])
    lines.extend(["", f"> 当前主题：{topic}。Research State 只保存候选状态，不能覆盖 SK canonical files。"])
    return "\n".join(lines)

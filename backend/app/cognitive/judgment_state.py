from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from app.db import ensure_schema, get_connection


def build_judgment_update(
    user_input: str,
    topic: str,
    previous_state: dict[str, Any],
    operator_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = _operator_list(operator_output, "evidence_ledger")
    risks = _merge_unique(
        list(previous_state.get("risks") or [])[-8:],
        _operator_list(operator_output, "risks"),
        _infer_risks(user_input),
    )
    unresolved = _merge_unique(
        list(previous_state.get("unresolved_questions") or [])[-8:],
        _operator_list(operator_output, "missing_evidence"),
        _infer_unresolved(user_input),
    )
    current_judgment = _infer_judgment(user_input, topic, operator_output)
    why = _infer_why(user_input, operator_output, evidence)
    return {
        "current_judgment": current_judgment,
        "why": why,
        "evidence": evidence[:12],
        "risks": risks[:12],
        "unresolved_questions": unresolved[:12],
        "next_question": _next_question(topic, unresolved, risks),
    }


def add_judgment(
    session_id: str,
    entity_slug: str,
    judgment: str,
    why: str,
    evidence: list[dict[str, Any]],
    risks: list[str],
    unresolved: list[str],
) -> dict[str, Any]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(MAX(step), 0) + 1 AS next_step FROM cognitive_judgments WHERE session_id = %s;",
                (session_id,),
            )
            step = int(cursor.fetchone()["next_step"])
            cursor.execute(
                """
                INSERT INTO cognitive_judgments (
                    session_id, entity_slug, step, judgment, why,
                    evidence_json, risks_json, unresolved_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, session_id, created_at, entity_slug, step, judgment,
                          why, evidence_json, risks_json, unresolved_json;
                """,
                (
                    session_id,
                    entity_slug,
                    step,
                    judgment,
                    why,
                    Jsonb(evidence),
                    Jsonb(risks),
                    Jsonb(unresolved),
                ),
            )
            return _normalize_judgment(cursor.fetchone())


def list_judgments(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    ensure_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, session_id, created_at, entity_slug, step, judgment,
                       why, evidence_json, risks_json, unresolved_json
                FROM cognitive_judgments
                WHERE session_id = %s
                ORDER BY step DESC
                LIMIT %s;
                """,
                (session_id, limit),
            )
            return [_normalize_judgment(row) for row in reversed(cursor.fetchall())]


def _operator_list(operator_output: dict[str, Any] | None, key: str) -> list[Any]:
    if not operator_output:
        return []
    value = operator_output.get(key)
    if value is None:
        value = (operator_output.get("structured_output") or {}).get(key)
    return value if isinstance(value, list) else []


def _infer_judgment(user_input: str, topic: str, operator_output: dict[str, Any] | None) -> str:
    if operator_output and operator_output.get("conclusion"):
        return str(operator_output["conclusion"])
    text = user_input.strip()
    if any(marker in text for marker in ["会不会", "是不是", "像不像", "可能", "风险"]):
        return f"当前把问题暂挂在「{topic}」上：这是一个待验证判断，不应直接当作结论。"
    return f"当前主题是「{topic}」；系统会延续这个认知对象继续组织证据、风险和下一步问题。"


def _infer_why(user_input: str, operator_output: dict[str, Any] | None, evidence: list[dict[str, Any]]) -> str:
    if evidence:
        return "已有候选来源进入证据账本，但仍需人工复核和 canonical files 校准。"
    if operator_output and operator_output.get("minimal_next_step"):
        return str(operator_output["minimal_next_step"])
    return f"本轮输入触发的是思考延续：{user_input[:160]}"


def _infer_risks(user_input: str) -> list[str]:
    risks = ["当前判断不能覆盖 SK canonical files。"]
    if any(marker in user_input for marker in ["卖药", "商业化", "推荐", "渠道", "信任", "冲突"]):
        risks.append("可能存在诊断结果与商业转化之间的信任冲突。")
    if any(marker in user_input for marker in ["医疗", "诊断", "健康"]):
        risks.append("健康/医疗相关判断需要更高证据标准。")
    return risks


def _infer_unresolved(user_input: str) -> list[str]:
    questions: list[str] = []
    if any(marker in user_input for marker in ["卖药", "商业化", "推荐", "渠道"]):
        questions.append("是否会从诊断入口滑向卖药或商业推荐渠道？")
        questions.append("产品推荐是否与商业转化绑定？")
        questions.append("用户是否能区分诊断建议与销售建议？")
    if any(marker in user_input for marker in ["留存", "复购", "使用"]):
        questions.append("用户留存和复用频率是否有可靠证据？")
    if not questions:
        questions.append("下一步最需要补哪类证据来支撑或推翻当前判断？")
    return questions


def _next_question(topic: str, unresolved: list[str], risks: list[str]) -> str:
    if unresolved:
        return unresolved[0]
    if risks:
        return f"围绕「{topic}」，先验证最大风险：{risks[0]}"
    return f"围绕「{topic}」，继续补一个能改变判断的关键证据。"


def _merge_unique(*groups: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if isinstance(item, dict):
                text = str(item.get("claim") or item.get("note") or item)
            else:
                text = str(item)
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
    return result


def _normalize_judgment(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    if result.get("created_at") is not None:
        result["created_at"] = result["created_at"].isoformat()
    result["evidence"] = result.pop("evidence_json") or []
    result["risks"] = result.pop("risks_json") or []
    result["unresolved"] = result.pop("unresolved_json") or []
    return result

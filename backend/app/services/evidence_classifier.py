from __future__ import annotations

from typing import Any


def candidate_level_for_source(source_type: str) -> str:
    normalized = (source_type or "").strip().lower()
    if normalized == "official":
        return "A_candidate"
    if normalized == "app_store":
        return "B_candidate"
    if normalized == "company_profile":
        return "B_candidate"
    if normalized == "media":
        return "B_candidate"
    if normalized == "community":
        return "C_candidate"
    return "X_candidate"


def confidence_for_source(source_type: str) -> float:
    normalized = (source_type or "").strip().lower()
    if normalized == "official":
        return 0.78
    if normalized == "app_store":
        return 0.7
    if normalized == "company_profile":
        return 0.64
    if normalized == "media":
        return 0.62
    if normalized == "community":
        return 0.4
    return 0.2


def web_result_to_evidence(claim: str, result: dict[str, Any]) -> dict[str, Any]:
    source_type = str(result.get("source_type") or "unknown")
    source_reason = str(result.get("source_reason") or "")
    return {
        "claim": claim,
        "source_title": result.get("title") or "",
        "source_url": result.get("url") or "",
        "source_type": source_type,
        "source_reason": source_reason,
        "evidence_level": _candidate_level_for_result(source_type, source_reason, result),
        "confidence": confidence_for_source(source_type),
        "fetched_at": result.get("fetched_at"),
        "note": "联网结果只是候选证据，不能覆盖 canonical files，不能自动入库。",
    }


def _candidate_level_for_result(source_type: str, source_reason: str, result: dict[str, Any]) -> str:
    text = " ".join(str(result.get(key) or "").lower() for key in ["title", "snippet", "url"])
    if source_type == "app_store" and any(
        marker in text for marker in ["rating", "review", "updated", "downloads", "installs", "评分", "评论"]
    ):
        return "A_candidate_for_app_metadata"
    if source_type == "media" and "announcement wire" in source_reason:
        return "A_candidate_for_announcement"
    return candidate_level_for_source(source_type)

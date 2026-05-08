from __future__ import annotations


def expand_search_queries(
    *,
    role_id: str,
    task_type: str,
    user_input: str,
    explicit_queries: list[str] | None = None,
    limit: int = 5,
) -> list[str]:
    explicit = _clean_queries(explicit_queries)
    if explicit:
        return explicit[:limit]

    base = _normalize_subject(user_input)
    if not base:
        return []

    if role_id == "deep_researcher_role" or task_type == "deep_research":
        return _dedupe(
            [
                _brand_query(base),
                f"{_brand_query(base)} startup",
                f"{_brand_query(base)} healthcare",
                f"{_brand_query(base)} founder",
                f"{_brand_query(base)} funding",
            ]
        )[:limit]

    if role_id == "product_teardown_role" or task_type == "product_teardown":
        return _dedupe(
            [
                _brand_query(base),
                f"{_brand_query(base)} pricing",
                f"{_brand_query(base)} revenue",
                f"{_brand_query(base)} funding",
                f"{_brand_query(base)} competitors",
                f"{_brand_query(base)} reviews reddit",
            ]
        )[:limit]

    if role_id == "article_publish_check_role" or task_type == "article_publish_check":
        return _dedupe(
            [
                _brand_query(base),
                f"{_brand_query(base)} latest",
                f"{_brand_query(base)} official",
                f"{_brand_query(base)} announcement",
            ]
        )[:limit]

    return [base][:limit]


def _clean_queries(queries: list[str] | None) -> list[str]:
    return _dedupe([item.strip() for item in (queries or []) if item and item.strip()])


def _normalize_subject(value: str) -> str:
    compact = " ".join((value or "").replace("\n", " ").split())
    return compact[:120]


def _brand_query(value: str) -> str:
    compact = _normalize_subject(value)
    if compact.lower() == "hippocratic":
        return "Hippocratic AI"
    return compact


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        results.append(value)
    return results
